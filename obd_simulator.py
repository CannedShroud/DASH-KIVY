
import socket
import time
import random
import threading
import sys
import os

# Configuration
HOST = '0.0.0.0'
PORT = int(os.environ.get("OBD_PORT", 35000))

# OBD Data State
class VehicleState:
    def __init__(self):
        self.rpm = 800.0
        self.speed = 0.0
        self.throttle = 0.0
        self.coolant = 85.0
        self.oil = 90.0
        self.intake_temp = 30.0
        self.voltage = 14.1
        self.load = 20.0
        self.map_pressure = 100.0 # kPa
        self.timing = 15.0 # degrees
        self.stft = 0.0
        self.ltft = 2.3
        self.maf = 5.0
        
        # Simulation flags
        self.target_rpm = 800
        self.accelerating = False

    def update(self):
        """Updates vehicle physics"""
        # RPM Logic
        if self.accelerating:
            self.target_rpm = 6500
            step = 150
        else:
            self.target_rpm = 800
            step = 100
            
        if self.rpm < self.target_rpm:
            self.rpm += step + random.uniform(-10, 10)
        elif self.rpm > self.target_rpm:
            self.rpm -= step + random.uniform(-10, 10)
            
        # Clamp RPM
        self.rpm = max(0, min(self.rpm, 7200))
        
        # Derived values
        self.throttle = (self.rpm / 7000.0) * 100.0 if self.accelerating else 0.0
        self.speed = (self.rpm / 200.0) if self.rpm > 1000 else 0
        
        # Boost/Vacuum (MAP)
        # Idle ~30kPa (vacuum), WOT ~200kPa (boost)
        if self.throttle > 50:
            self.map_pressure = 100 + ((self.throttle - 50) * 2) # Boost
        else:
            self.map_pressure = 30 + (self.throttle * 1.4) # Vacuum to Atmos
            
        # Random noise
        self.coolant += random.uniform(-0.1, 0.1)
        self.voltage = 13.8 + random.uniform(-0.2, 0.4)
        
        # Clamp Temps
        self.coolant = max(80, min(self.coolant, 105))

state = VehicleState()

def physics_loop():
    while True:
        state.update()
        # Toggle acceleration periodically
        if random.random() < 0.05:
            state.accelerating = not state.accelerating
        time.sleep(0.05)

def format_hex_byte(val):
    return f"{int(val):02X}"

def handle_pid(pid_hex):
    """Returns the hex data for a given PID"""
    # MAP: Mode 01
    
    # Standard PIDs
    if pid_hex == "0C": # RPM (2 bytes, 1/4 rpm)
        val = int(state.rpm * 4)
        return f"{val:04X}"
        
    elif pid_hex == "0D": # Speed (1 byte, km/h)
        return format_hex_byte(state.speed)
        
    elif pid_hex == "05": # Coolant (1 byte, A-40)
        return format_hex_byte(state.coolant + 40)
        
    elif pid_hex == "5C": # Oil Temp (1 byte, A-40)
        return format_hex_byte(state.oil + 40)
        
    elif pid_hex == "0F": # Intake Temp (1 byte, A-40)
        return format_hex_byte(state.intake_temp + 40)
        
    elif pid_hex == "0B": # MAP (1 byte, kPa)
        return format_hex_byte(state.map_pressure)
        
    elif pid_hex == "11": # Throttle (1 byte, A*100/255)
        val = int((state.throttle * 255) / 100)
        return format_hex_byte(val)
        
    elif pid_hex == "42": # Voltage (2 bytes, A/1000)
        val = int(state.voltage * 1000)
        return f"{val:04X}"
        
    elif pid_hex == "04": # Load (1 byte)
        val = int((state.load * 255) / 100)
        return format_hex_byte(val)
        
    elif pid_hex == "06": # STFT (1 byte)
        # (A - 128) * 100/128
        val = int((state.stft * 1.28) + 128)
        return format_hex_byte(val)

    elif pid_hex == "07": # LTFT
        val = int((state.ltft * 1.28) + 128)
        return format_hex_byte(val)
    
    elif pid_hex == "0E": # Timing (1 byte, A/2 - 64)
        val = int((state.timing + 64) * 2) 
        return format_hex_byte(val)
        
    elif pid_hex == "33": # Baro (1 byte, kPa)
        return "64" # 100 kPa
        
    elif pid_hex == "44": # AFR (2 bytes, lambda)
        return "8000" # 1.0 lambda

    # Default to 00 if unknown
    return "00"

def handle_client(conn, addr):
    print(f"[*] Connected by {addr}")
    buffer = ""
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            
            raw_msg = data.decode('utf-8', errors='ignore')
            # Handle multiple commands in one packet, usually separated by \r
            # BUT ELM327 receives character by character usually.
            # We'll assume the client sends a full command ending with \r
            
            # Simple buffer accumulation
            buffer += raw_msg
            
            while '\r' in buffer:
                cmd_end = buffer.find('\r')
                cmd = buffer[:cmd_end].strip()
                buffer = buffer[cmd_end+1:]
                
                if not cmd:
                    continue
                    
                # print(f"[RX] {cmd}")
                
                response = ""
                
                # --- COMMAND HANDLING ---
                
                # AT Commands (Configuration)
                if cmd.startswith("AT"):
                    if cmd == "ATZ":
                        response = "\r\nELM327 v1.5\r\nOK"
                    elif cmd == "ATI":
                        response = "ELM327 v1.5"
                    else:
                        response = "OK"
                
                # Mode 01 Commands (Data)
                # Formats: "010C" (Single) or "010C0D05..." (Batch)
                elif cmd.startswith("01"):
                    pids_str = cmd[2:]
                    # Parse PIDs in pairs of 2 chars
                    # e.g. 0C 0D 05
                    request_pids = [pids_str[i:i+2] for i in range(0, len(pids_str), 2)]
                    
                    data_bytes = ""
                    for pid in request_pids:
                        data_bytes += handle_pid(pid)
                    
                    # Echo the command? 
                    # Usually ELM327 echos unless ATE0.
                    # We will just send the response 41 ...
                    # The response format for multiple PIDs is contiguous
                    # 41 [PID1] [DATA1] [PID2] [DATA2] ...
                    
                    # Wait... standard ELM327 doesn't natively support arbitrary batching 
                    # like "010C0D" in one go unless it's a specific CAN request, 
                    # but python-obd and many apps use this trick if the protocol allows.
                    # wifi.py sends "010C0B0E..." as one string.
                    # We need to constructing the response:
                    # 41 + payload
                    
                    # However, strictly speaking, 01 0C 0D is NOT standard OBD-II. 
                    # Standard is one PID per request.
                    # But some "Fast" implementations support it or the ECU supports it.
                    # wifi.py expects the response to contain the PIDs too?
                    # Let's check wifi.py:
                    #     parse_batch_response checks: if current_data.startswith(pid_hex): ...
                    # So wifi.py expects the response to include the PID before the data.
                    # e.g. 41 0C [2bytes] 0D [1byte] ...
                    
                    sim_response_payload = ""
                    for pid in request_pids:
                        sim_response_payload += pid
                        sim_response_payload += handle_pid(pid)
                        
                    response = f"41{sim_response_payload}"
                    
                else:
                    response = "?"
                    
                # Finalize Response
                # ELM327 format:
                # [Data]\r\n>
                
                full_response = f"{response}\r\n>"
                conn.sendall(full_response.encode('ascii'))
                
    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        conn.close()
        print(f"[*] Connection closed {addr}")

def main():
    # Start physics thread
    t = threading.Thread(target=physics_loop, daemon=True)
    t.start()
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((HOST, PORT))
        server.listen(5)
        print(f"[*] OBD Simulator listening on {HOST}:{PORT}")
        print("    Press Ctrl+C to stop.")
        
        while True:
            conn, addr = server.accept()
            # Handle client in a thread
            ct = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            ct.start()
            
    except KeyboardInterrupt:
        print("\n[*] Stopping simulator...")
    except Exception as e:
        print(f"\n[!] Server error: {e}")
    finally:
        server.close()

if __name__ == "__main__":
    main()
