
import socket
import time
import random
import threading
import sys
import os
from enum import Enum

# Configuration
HOST = '0.0.0.0'
PORT = int(os.environ.get("OBD_PORT", 35000))

class Scenario(Enum):
    COLD_START = 1
    NORMAL_ECO = 2
    AGGRESSIVE = 3
    ISSUES = 4

# OBD Data State
class VehicleState:
    def __init__(self):
        self.scenario = Scenario.COLD_START
        self.start_time = time.time()
        self.scenario_timer = time.time()
        
        # Physics State
        self.rpm = 800.0
        self.speed = 0.0
        self.throttle = 0.0
        
        # Temperatures
        self.coolant = 20.0
        self.oil = 20.0
        self.intake_temp = 25.0
        
        # Electrical
        self.voltage = 14.1
        
        # Air/Fuel
        self.load = 20.0
        self.map_pressure = 30.0 # kPa
        self.timing = 15.0 # degrees
        self.stft = 0.0
        self.ltft = 0.0
        self.maf = 5.0
        self.afr_lambda = 1.0
        
        # Simulation Internal
        self.target_rpm = 800
        self.accelerating = False

    def change_scenario(self):
        # Cycle scenarios every 30 seconds
        now = time.time()
        if now - self.scenario_timer > 30:
            modes = list(Scenario)
            current_idx = modes.index(self.scenario)
            next_idx = (current_idx + 1) % len(modes)
            self.scenario = modes[next_idx]
            self.scenario_timer = now
            print(f"[*] Switching Scenario to: {self.scenario.name}")
            
            # Reset some values on switch
            if self.scenario == Scenario.COLD_START:
                self.coolant = 20
                self.oil = 20
            elif self.scenario == Scenario.ISSUES:
                self.voltage = 11.5 # Start low
                self.ltft = 10 # Lean condition?
            

    def update(self):
        """Updates vehicle physics based on current scenario"""
        self.change_scenario()
        
        # --- SCENARIO LOGIC ---
        if self.scenario == Scenario.COLD_START:
            # High Idle, Warming up
            target_idle = 1200 if self.coolant < 50 else 800
            self.target_rpm = target_idle + (random.uniform(-20, 20))
            self.throttle = 0
            
            # Warmup
            self.coolant += 0.2
            self.oil += 0.1
            
            self.voltage = 14.2
            self.afr_lambda = 0.95 # Rich for warmup
            self.intake_temp = 25

        elif self.scenario == Scenario.NORMAL_ECO:
            # Gentle driving
            if random.random() < 0.05: 
                self.accelerating = not self.accelerating
            
            self.target_rpm = 2500 if self.accelerating else 800
            step = 50
            
            self.coolant = 90 + random.uniform(-2, 2)
            self.oil = 95 + random.uniform(-1, 1)
            self.voltage = 13.8 + random.uniform(-0.1, 0.1)
            self.afr_lambda = 1.0 # Stoich
            self.intake_temp = 35
            
            # Trims good
            self.stft = random.uniform(-3, 3)
            self.ltft = random.uniform(-2, 2)

        elif self.scenario == Scenario.AGGRESSIVE:
            # WOT pulls
            if random.random() < 0.1:
                self.accelerating = not self.accelerating
            
            self.target_rpm = 6500 if self.accelerating else 3000
            step = 300 # Fast revs
            
            self.coolant = 95 + random.uniform(0, 5)
            self.oil = 105 + random.uniform(0, 5)
            self.afr_lambda = 0.85 if self.accelerating else 1.0 # Rich power
            self.voltage = 14.4
            
        elif self.scenario == Scenario.ISSUES:
            # Problems
            self.target_rpm = 800 + random.uniform(-100, 100) # Rough idle
            self.voltage = 11.2 + random.uniform(-0.5, 0.5) # Dying battery/Alt
            self.intake_temp = 65 + random.uniform(0, 5) # Heat soak
            self.ltft = -15 # Rich leak?
            self.stft = -10
            self.coolant = 108 # Overheating
            self.oil = 115
            self.afr_lambda = 0.8 # Running rich
            
        # --- PHYSICS ---
        
        # RPM smoothing
        if self.rpm < self.target_rpm:
            self.rpm += (self.target_rpm - self.rpm) * 0.1
        else:
            self.rpm -= (self.rpm - self.target_rpm) * 0.1
            
        # Clamp RPM
        self.rpm = max(0, min(self.rpm, 7200))
        
        # Speed (gear ratio simulation)
        self.speed = (self.rpm / 200.0) if self.rpm > 1000 else 0
        
        # Load / Map
        if self.scenario == Scenario.AGGRESSIVE:
            self.throttle = (self.rpm / 7000) * 100
            self.load = 80 + (self.throttle * 0.2)
        else:
            self.throttle = (self.rpm / 3000) * 30
            self.load = 20 + (self.throttle * 0.5)
            
        if self.throttle > 50:
            self.map_pressure = 100 + ((self.throttle - 50) * 2) # Boost
        else:
            self.map_pressure = 30 + (self.throttle * 1.4) # Vacuum
            
        # Timing (simple map)
        self.timing = 25 - (self.load / 5)

        # Limits
        self.coolant = max(0, min(self.coolant, 130))
        self.oil = max(0, min(self.oil, 140))

state = VehicleState()

def physics_loop():
    while True:
        state.update()
        time.sleep(0.1)

def format_hex_byte(val):
    val = max(0, min(int(val), 255))
    return f"{val:02X}"

def handle_pid(pid_hex):
    """Returns the hex data for a given PID"""
    
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
        val = int((state.stft / (100.0/128.0)) + 128)
        return format_hex_byte(val)

    elif pid_hex == "07": # LTFT
        val = int((state.ltft / (100.0/128.0)) + 128)
        return format_hex_byte(val)
    
    elif pid_hex == "0E": # Timing (1 byte, A/2 - 64)
        val = int((state.timing + 64) * 2) 
        return format_hex_byte(val)
        
    elif pid_hex == "33": # Baro (1 byte, kPa)
        return "64" # 100 kPa
        
    elif pid_hex == "44": # AFR (2 bytes, lambda)
        # Ratio = A / 32768
        val = int(state.afr_lambda * 32768)
        return f"{val:04X}"

    return "00"

def handle_client(conn, addr):
    print(f"[*] Connected by {addr}")
    buffer = ""
    try:
        while True:
            data = conn.recv(1024)
            if not data: break
            
            raw_msg = data.decode('utf-8', errors='ignore')
            buffer += raw_msg
            
            while '\r' in buffer:
                cmd_end = buffer.find('\r')
                cmd = buffer[:cmd_end].strip()
                buffer = buffer[cmd_end+1:]
                
                if not cmd: continue
                    
                response = ""
                
                if cmd.startswith("AT"):
                    if cmd == "ATZ": response = "\r\nELM327 v1.5\r\nOK"
                    else: response = "OK"
                
                elif cmd.startswith("01"):
                    pids_str = cmd[2:]
                    request_pids = [pids_str[i:i+2] for i in range(0, len(pids_str), 2)]
                    
                    sim_response_payload = ""
                    for pid in request_pids:
                        sim_response_payload += pid
                        sim_response_payload += handle_pid(pid)
                        
                    response = f"41{sim_response_payload}"
                else:
                    response = "?"
                    
                full_response = f"{response}\r\n>"
                conn.sendall(full_response.encode('ascii'))
                
    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        conn.close()

def main():
    t = threading.Thread(target=physics_loop, daemon=True)
    t.start()
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((HOST, PORT))
        server.listen(5)
        print(f"[*] Advanced OBD Simulator (Scenarios: Cold -> Eco -> Aggro -> Issues)")
        print(f"[*] Listening on {HOST}:{PORT}")
        
        while True:
            conn, addr = server.accept()
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
