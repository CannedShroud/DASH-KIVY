from kivy.config import Config
from kivy.uix.relativelayout import RelativeLayout
Config.set("graphics", "fullscreen", "auto")
Config.set('graphics', 'show_cursor', '0')

from kivy.core.window import Window
Window.show_cursor = False

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.widget import Widget
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.checkbox import CheckBox
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup

from kivy.graphics import Color, Line
from kivy.uix.image import Image
from kivy.graphics import Rectangle, Rotate, PushMatrix, PopMatrix, Translate
from kivy.properties import NumericProperty, StringProperty
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.text import Label as CoreLabel
from kivy.animation import Animation
from kivy.core.window import Window
import threading
import re
from math import inf
import random
import obd
from enum import Enum
from os import path
import time
import socket
import select
import os
from config_manager import config_manager

USE_FAKE_OBD = False

DIAL_MIN = 18
DIAL_MAX = -110
OBD_WIFI_IP = os.environ.get("OBD_HOST", "192.168.0.10")
OBD_WIFI_PORT = int(os.environ.get("OBD_PORT", 35000))
GAUGE_UPDATE_INTERVAL = 1.0 / 60.0
ASSETS_ICONS_PATH = "./assets/icons/"
ASSETS_ICONS_PATH = "./assets/icons/"
ASSETS_FONTS_PATH = "./assets/fonts"
MAX_GAUGES = 6

class PID(Enum):
    BARO = "BAROMETRIC_PRESSURE"
    BOOST = "MANIFOLD_PRESSURE"
    IAT = "IAT"
    AFR = "AFR_C"
    TIMING = "IGNITION_TIMING"
    COOLANT_TEMP = "COOLANT_TEMP"
    OIL_TEMP = "OIL_TEMP"
    VOLTAGE = "VOLTAGE"
    RPM = "ENGINE_RPM"
    THROTTLE = "THROTTLE_POSITION"
    SPEED = "SPEED"
    LTFT = "LTFT"
    STFT = "STFT"
    LOAD = "ENGINE_LOAD"

# --- FIXED DATA DICTIONARY ---
DATA = {
    PID.BARO: { "name": "Barometer", "pid": "33", "unit": "psi", "convert": lambda A: A * 0.145, "bytes": 1, "dial_min": 0, "dial_max": 20, "value": 14.5, "min_read": inf, "max_read": -inf, "icon": "boost_pressure.png", "precision": 1 },
    PID.BOOST: { "name": "Boost", "pid": "0B", "unit": "psi", "convert": lambda A: (A * 0.145) - 14.5, "bytes": 1, "dial_min": -20, "dial_max": 30, "value": 0, "min_read": inf, "max_read": -inf, "icon": "boost_pressure.png", "precision": 1 },
    PID.IAT: { "name": "Intake Air Temp", "pid": "0F", "unit": "°C", "convert": lambda A: A - 40, "bytes": 1, "dial_min": 0, "dial_max": 80, "value": 40, "min_read": inf, "max_read": -inf, "icon": "iat.png", "precision": 0 },
    PID.AFR: { "name": "Commanded AFR", "pid": "44", "unit": "λ", "convert": lambda A: A / 32768.0, "bytes": 2, "dial_min": 0.7, "dial_max": 1.3, "value": 1.0, "min_read": float('inf'), "max_read": float('-inf'), "icon": "afr.png", "precision": 2 },
    PID.TIMING: { "name": "Timing Advance", "pid": "0E", "unit": "°", "convert": lambda A: (A / 2.0) - 64.0, "bytes": 1, "dial_min": -20, "dial_max": 60, "value": 0, "min_read": float('inf'), "max_read": float('-inf'), "icon": "timing.png", "precision": 0 },
    PID.COOLANT_TEMP: { "name": "Coolant Temp", "pid": "05", "unit": "°C", "convert": lambda A: A - 40, "bytes": 1, "dial_min": 40, "dial_max": 120, "value": 90, "min_read": inf, "max_read": -inf, "icon": "coolant_temp.png", "precision": 0 },
    PID.OIL_TEMP: { "name": "Oil Temp", "pid": "5C", "unit": "°C", "convert": lambda A: A - 40, "bytes": 1, "dial_min": 40, "dial_max": 120, "value": 90, "min_read": inf, "max_read": -inf, "icon": "oil_temp.png", "precision": 0 },
    PID.VOLTAGE: { "name": "Voltage", "pid": "42", "unit": "V", "convert": lambda A: A / 1000.0, "bytes": 2, "dial_min": 5, "dial_max": 20, "value": 12, "min_read": inf, "max_read": -inf, "icon": "battery.png", "precision": 1 },
    PID.RPM: { "name": "RPM", "pid": "0C", "unit": "rpm", "convert": lambda A: A / 4.0, "bytes": 2, "dial_min": 0, "dial_max": 7000, "value": 800, "min_read": float('inf'), "max_read": float('-inf'), "icon": "speedo.png", "precision": 0 },
    PID.THROTTLE: { "name": "Throttle", "pid": "11", "unit": "%", "convert": lambda A: (A * 100.0) / 255.0, "bytes": 1, "dial_min": 0, "dial_max": 100, "value": 0, "min_read": float('inf'), "max_read": float('-inf'), "icon": "throttlebody.png", "precision": 0 },
    PID.SPEED: { "name": "Speed", "pid": "0D", "unit": "km/h", "convert": lambda A: A, "bytes": 1, "dial_min": 0, "dial_max": 180, "value": 0, "min_read": float('inf'), "max_read": float('-inf'), "icon": "speedo.png", "precision": 0 },
    PID.LTFT: { "name": "LTFT", "pid": "07", "unit": "%", "convert": lambda A: (A - 128) * (100.0 / 128.0), "bytes": 1, "dial_min": -25, "dial_max": 25, "value": 0, "min_read": float('inf'), "max_read": float('-inf'), "icon": "trim.png", "precision": 1 },
    PID.STFT: { "name": "STFT", "pid": "06", "unit": "%", "convert": lambda A: (A - 128) * (100.0 / 128.0), "bytes": 1, "dial_min": -25, "dial_max": 25, "value": 0, "min_read": float('inf'), "max_read": float('-inf'), "icon": "trim.png", "precision": 1 },
    PID.LOAD: { "name": "Engine Load", "pid": "04", "unit": "%", "convert": lambda A: (A * 100.0) / 255.0, "bytes": 1, "dial_min": 0, "dial_max": 100, "value": 0, "min_read": float('inf'), "max_read": float('-inf'), "icon": "load.png", "precision": 0 },
}

# ============================================================================
#  USER CONFIGURATION SECTION
# ============================================================================

# 1. FAST PIDS: Updated instantly.
# WARNING: Keep total response bytes <= 7 for instant updates.
# Calculation: 1 byte (Header) + Sum(1 byte PID + N bytes Data for each PID)
FAST_PIDS_KEYS = config_manager.get("fast_pids")
FAST_PIDS = [getattr(PID, k) for k in FAST_PIDS_KEYS if hasattr(PID, k)]

# 2. SLOW PIDS: Updated every 10th cycle (Temps, Voltages, etc)
# Focused on Thermal Management (Altroz weakness) and General Health.
SLOW_PIDS_KEYS = config_manager.get("slow_pids")
SLOW_PIDS = [getattr(PID, k) for k in SLOW_PIDS_KEYS if hasattr(PID, k)]

# 3. UI CONFIG: Which gauges/cells appear on screen
GAUGES_KEYS = config_manager.get("gauges")
GAUGES_TO_SHOW = [getattr(PID, k) for k in GAUGES_KEYS if hasattr(PID, k)]

DATACELLS_KEYS = config_manager.get("datacells")
DATACELLS_TO_SHOW = [getattr(PID, k) for k in DATACELLS_KEYS if hasattr(PID, k)]

# ============================================================================

class AssistKey(Enum):
    ECO_STATUS = "eco_status"
    SHIFT_HINT = "shift_hint"
    WARMUP_STATUS = "warmup_status"
    RESPONSIVENESS_LABEL = "responsiveness_label"
    BATTERY_STATUS = "battery_status"
    THROTTLE_STYLE = "throttle_style"

DRIVER_ASSISTS_STATE = {
    AssistKey.ECO_STATUS: { "name": "Eco Status", "value": "--", "show": True, "icon": "eco.png" },
    AssistKey.SHIFT_HINT: { "name": "Shift Hint", "value": "--", "show": True, "icon": "shift.png" },
    AssistKey.WARMUP_STATUS: { "name": "Engine Warmup Status", "value": "--", "show": True, "icon": "enginecold.png" },
    AssistKey.RESPONSIVENESS_LABEL: { "name": "Engine Responsiveness", "value": "--", "show": True, "icon": "responsiveness.png" },
    AssistKey.BATTERY_STATUS: { "name": "Battery Status", "value": "--", "show": True, "icon": "batterywarning.png" },
    AssistKey.THROTTLE_STYLE: { "name": "Drive Style", "value": "--", "show": True, "icon": "drivestyle.png" }
}

DRIVER_ASSISTS_INTERNAL_STATE = { "prev_throttle": None }
WARNINGS_KEYS = config_manager.get("warnings")
WARNINGS_TO_SHOW = [getattr(AssistKey, k) for k in WARNINGS_KEYS if hasattr(AssistKey, k)]

# --- HELPER FUNCTIONS FOR CONFIGURATION ---

def validate_batch_size(pids, batch_name):
    """Calculates response size and warns if it exceeds Single Frame (7 byte) limit."""
    total_bytes = 1 # Response header '41'
    for pid in pids:
        total_bytes += 1 # The PID echo
        total_bytes += DATA[pid]["bytes"] # The data bytes
    
    print(f"[*] Config Check: {batch_name} Response Size = {total_bytes} bytes")
    
    if total_bytes > 7:
        print(f"[!] WARNING: {batch_name} size ({total_bytes}B) exceeds 7 bytes!")
        print(f"    This will trigger Multi-Frame responses (slower).")
        print(f"    Consider removing PIDs from {batch_name} to restore instant speed.")
    else:
        print(f"[*] {batch_name} fits in Single Frame. Maximum Speed Enabled.")

def generate_batch_cmd(pids):
    """Generates the hex command string from a list of PIDs."""
    # Start with Mode 01
    cmd_str = "01"
    for pid in pids:
        cmd_str += DATA[pid]["pid"]
    cmd_str += "\r"
    return cmd_str.encode('ascii')

# ----------------------------------------

def raw_obd_connect():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((OBD_WIFI_IP, OBD_WIFI_PORT))
        
        commands = [b"ATZ\r", b"ATE0\r", b"ATL0\r", b"ATS0\r", b"ATH0\r", b"ATSP0\r", b"0100\r"]
        for cmd in commands:
            s.send(cmd)
            buffer = b""
            while b">" not in buffer:
                try:
                    chunk = s.recv(1024)
                    if not chunk: break
                    buffer += chunk
                except socket.timeout:
                    break
            # print(f"Init cmd {cmd.strip()} -> {buffer.strip()}")
        print("[*] Raw High-Speed OBD Connection Established")
        return s
    except Exception as e:
        print(f"[!] Raw Connection Failed: {e}")
        return None

def parse_batch_response(buffer, requested_pids):
    try:
        raw_str = buffer.decode('utf-8', errors='ignore').strip()
    except:
        return

    if ':' in raw_str:
        lines = raw_str.split('\r')
        clean_hex = ""
        for line in lines:
            line = line.strip()
            if ':' in line:
                clean_hex += line.split(':')[1]
    else:
        clean_hex = raw_str.replace('\r', '').replace('\n', '')

    clean_hex = clean_hex.replace(' ', '').replace('>', '')
    response_start = clean_hex.find("41")
    if response_start == -1:
        return

    current_data = clean_hex[response_start + 2:]

    for pid_key in requested_pids:
        pid_hex = DATA[pid_key]["pid"]
        byte_count = DATA[pid_key]["bytes"]
        hex_len = byte_count * 2
        
        if current_data.startswith(pid_hex):
            try:
                raw_val_hex = current_data[2 : 2 + hex_len]
                val_int = int(raw_val_hex, 16)
                update_data_entry(pid_key, val_int)
                current_data = current_data[2 + hex_len:]
            except ValueError:
                break
        else:
            pass

def update_data_entry(pid_key, raw_val):
    try:
        entry = DATA[pid_key]
        val = entry["convert"](raw_val)
        precision = entry["precision"]
        truncated_value = f"{val:.{precision}f}"
        
        entry["value"] = truncated_value
        entry["min_read"] = str(min(float(entry["min_read"]), float(truncated_value)))
        entry["max_read"] = str(max(float(entry["max_read"]), float(truncated_value)))
    except Exception as e:
        print(f"[!] Update error for {pid_key}: {e}")

def start_obd_polling():
    if USE_FAKE_OBD:
        return

    # Validate Config on Startup
    validate_batch_size(FAST_PIDS, "FAST_PIDS")
    
    # Generate Commands dynamically
    batch_1_cmd = generate_batch_cmd(FAST_PIDS)
    batch_2_cmd = generate_batch_cmd(SLOW_PIDS)
    
    print(f"[*] Fast Command: {batch_1_cmd}")
    print(f"[*] Slow Command: {batch_2_cmd}")

    s = None
    while not s:
        s = raw_obd_connect()
        if not s: time.sleep(2)

    print("[*] Starting Ultra-Fast Batch Polling...")

    # Monitor Config Changes in Loop
    # We'll use a simple counter to check every N loops
    loop_count = 0
    
    while True:
        try:
            # Check for config reload (if main thread handled it, we just need to refresh lists)
            # Actually, the polling loop needs to know if PIDs changed.
            # We can check a shared flag or just check the config object directly.
            # Since ConfigManager is thread-safe effectively (GIL), we can check shared lists.
            pass # We will re-read PIDs from global config every loop or periodically
            
            # Re-read PIDs every 60 cycles (~1 sec) to catch updates
            if loop_count % 60 == 0:
                 # Update lists from config manager (which might have been reloaded by main thread)
                 # Note: ConfigManager might be reloaded by the UI thread, so we just read get().
                 
                 # Optimization: Only regenerate commands if lists changed
                 new_fast = [getattr(PID, k) for k in config_manager.get("fast_pids") if hasattr(PID, k)]
                 new_slow = [getattr(PID, k) for k in config_manager.get("slow_pids") if hasattr(PID, k)]
                 
                 if new_fast != FAST_PIDS or new_slow != SLOW_PIDS:
                     print("[*] Polling Loop: Detected PID list change. Regenerating commands.")
                     FAST_PIDS[:] = new_fast
                     SLOW_PIDS[:] = new_slow
                     batch_1_cmd = generate_batch_cmd(FAST_PIDS)
                     batch_2_cmd = generate_batch_cmd(SLOW_PIDS)

            # --- POLL FAST BATCH ---
            s.send(batch_1_cmd)
            buffer = b""
            while b">" not in buffer:
                chunk = s.recv(1024)
                if not chunk: raise ConnectionError("Lost connection")
                buffer += chunk
            
            parse_batch_response(buffer, FAST_PIDS)

            # --- POLL SLOW BATCH (Every 10th frame) ---
            if loop_count % 10 == 0:
                s.send(batch_2_cmd)
                buffer = b""
                while b">" not in buffer:
                    chunk = s.recv(1024)
                    if not chunk: raise ConnectionError("Lost connection")
                    buffer += chunk
                parse_batch_response(buffer, SLOW_PIDS)
            
            # Update driver assists periodically
            if loop_count % 5 == 0:
                update_driver_assists()

            loop_count += 1
            
        except (socket.timeout, ConnectionError, OSError):
            print("[!] Connection Lost. Reconnecting...")
            if s: s.close()
            s = None
            while not s:
                s = raw_obd_connect()
                if not s: time.sleep(2)
        except Exception as e:
            print(f"[!] Loop Exception: {e}")
            time.sleep(0.1)

# --- UI CLASSES START HERE (UNMODIFIED) ---

def update_driver_assists():
    try:
        throttle = float(DATA[PID.THROTTLE]["value"])
        load = float(DATA[PID.LOAD]["value"])
        # Check if AFR is available (it might be 0 if not polled yet or not in config)
        afr = float(DATA[PID.AFR]["value"]) if DATA[PID.AFR]["value"] != "--" else 14.7 
        rpm = float(DATA[PID.RPM]["value"])
        ltft = float(DATA[PID.LTFT]["value"])
        stft = float(DATA[PID.STFT]["value"])
        coolant = float(DATA[PID.COOLANT_TEMP]["value"])
        oil = float(DATA[PID.OIL_TEMP]["value"])
        timing = float(DATA[PID.TIMING]["value"])
        iat = float(DATA[PID.IAT]["value"])
        voltage = float(DATA[PID.VOLTAGE]["value"])

        # 1. Eco DrivingTrue
        eco = []
        if load > 80 or throttle > 70 or afr < 0.95:
            eco.append("Inefficient")
        elif throttle < 20 and rpm > 3000:
            eco.append("Upshift")
        if ltft < -5:
            eco.append("Rich trim")
        
        # Mapping to existing AssistKey.ECO_STATUS
        DRIVER_ASSISTS_STATE[AssistKey.ECO_STATUS]["value"] = ", ".join(eco) if eco else "ECO"

        # 2. Shift Suggestion
        if rpm > 3500 and throttle < 30:
            DRIVER_ASSISTS_STATE[AssistKey.SHIFT_HINT]["value"] = "SHIFT ^"
        elif rpm < 1500 and load > 80:
            DRIVER_ASSISTS_STATE[AssistKey.SHIFT_HINT]["value"] = "SHIFT v"
        else:
            DRIVER_ASSISTS_STATE[AssistKey.SHIFT_HINT]["value"] = "--"

        # 3. Warmup
        if oil < 40:
            DRIVER_ASSISTS_STATE[AssistKey.WARMUP_STATUS]["value"] = "Idle"
            # DRIVER_ASSISTS_STATE[AssistKey.WARMUP_STATUS]["show"] = True
        elif oil < 60 or coolant < 60:
            DRIVER_ASSISTS_STATE[AssistKey.WARMUP_STATUS]["value"]= "Gentle"
            # DRIVER_ASSISTS_STATE[AssistKey.WARMUP_STATUS]["show"] = True
        elif oil < 80 or coolant < 80:
            DRIVER_ASSISTS_STATE[AssistKey.WARMUP_STATUS]["value"]  = "Warm"
            # DRIVER_ASSISTS_STATE[AssistKey.WARMUP_STATUS]["show"] = True
        else:
            DRIVER_ASSISTS_STATE[AssistKey.WARMUP_STATUS]["value"] = "OK"
            # DRIVER_ASSISTS_STATE[AssistKey.WARMUP_STATUS]["show"] = False

        # 4. Responsiveness
        score = 100
        if iat > 50: score -= 20
        if abs(ltft) > 5: score -= 20
        if abs(stft) > 5: score -= 10
        if timing < 10: score -= 15
        if load < 20: score -= 10
        
        # label = "TUNED" if score > 80 else "OK" if score > 50 else "HEATSOAKED" if score > 30 else "DULL"
        # We don't have a label for Responsiveness in the original UI, 
        # but we have AssistKey.RESPONSIVENESS_LABEL defined in Python but not shown in WARNINGS_TO_SHOW by default.
        # We'll update usage if it exists.
        DRIVER_ASSISTS_STATE[AssistKey.RESPONSIVENESS_LABEL]["value"] = f"{score}%"

        # 5. Battery
        if voltage < 12.6:
            DRIVER_ASSISTS_STATE[AssistKey.BATTERY_STATUS]["value"] = "LOW"
        elif voltage > 14.7:
            DRIVER_ASSISTS_STATE[AssistKey.BATTERY_STATUS]["value"] = "HIGH"
        else:
            DRIVER_ASSISTS_STATE[AssistKey.BATTERY_STATUS]["value"] = "OK"

        # 6. Throttle Sensitivity Coach
        prev_throttle = DRIVER_ASSISTS_INTERNAL_STATE.get("prev_throttle")
        if prev_throttle is None:
            DRIVER_ASSISTS_INTERNAL_STATE["prev_throttle"] = throttle
            return

        delta_throttle = abs(throttle - prev_throttle)
        rate = delta_throttle / 0.5  # 0.5s interval

        if rate > 100:
            style = "AGGRESSIVE"
        elif rate > 20:
            style = "MODERATE"
        else:
            style = "SMOOTH"

        DRIVER_ASSISTS_STATE[AssistKey.THROTTLE_STYLE]["value"] = style
        DRIVER_ASSISTS_INTERNAL_STATE["prev_throttle"] = throttle

    except Exception as e:
        # print("[Assist Error]", e)
        pass

class DataCell(BoxLayout):
    def __init__(self, title, value, min_val, max_val, draw_top=False, draw_left=False, **kwargs):
        super().__init__(orientation='vertical', padding=5, **kwargs)
        self.draw_top = draw_top
        self.draw_left = draw_left
        self.title = Label(text=title, font_size='28sp', font_name=path.join(ASSETS_FONTS_PATH, "Barlow_Condensed", "BarlowCondensed-Regular.ttf"))
        self.value = Label(text=str(value), font_size='72sp', bold=True, font_name=path.join(ASSETS_FONTS_PATH, "Michroma", "Michroma-Regular.ttf"))
        self.min_val = Label(text=str(min_val), font_size='28sp', font_name=path.join(ASSETS_FONTS_PATH, "Barlow_Condensed", "BarlowCondensed-Bold.ttf"))
        self.separator = Label(text="|", font_size='28sp', font_name=path.join(ASSETS_FONTS_PATH, "Barlow_Condensed", "BarlowCondensed-Bold.ttf"))
        self.max_val = Label(text=str(max_val), font_size='28sp', font_name=path.join(ASSETS_FONTS_PATH, "Barlow_Condensed", "BarlowCondensed-Bold.ttf"))
        readings_box = BoxLayout(orientation='horizontal', spacing=0, size_hint=(None, None), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        readings_box.add_widget(self.min_val)
        readings_box.add_widget(self.separator)
        readings_box.add_widget(self.max_val)
        self.add_widget(self.title)
        self.add_widget(self.value)
        self.add_widget(readings_box)
        with self.canvas.after:
            if self.draw_top:
                self.top_line = Line(points=[self.x, self.top, self.right, self.top], width=1)
            if self.draw_left:
                self.left_line = Line(points=[self.x, self.y, self.x, self.top], width=1)
        self.bind(pos=self.update_lines, size=self.update_lines)
    def update_lines(self, *args):
        if hasattr(self, 'top_line'): self.top_line.points = [self.x, self.top, self.right, self.top]
        if hasattr(self, 'left_line'): self.left_line.points = [self.x, self.y, self.x, self.top]
    def update_readings(self, value, min_read, max_read):
        self.value.text = str(value)
        self.min_val.text = str(min_read)
        self.max_val.text = str(max_read)

class GaugeWidget(Widget):
    angle = NumericProperty(0)
    def __init__(self, label, icon_source, min_val, max_val, **kwargs):
        super().__init__(**kwargs)
        self.size = (320, 240)
        self.size_hint = (None, None)
        self.label_text = label
        self.icon_source = icon_source
        self.min_val = min_val
        self.max_val = max_val
        label_obj = CoreLabel(text=label, font_size=24, bold=True)
        label_obj.refresh()
        self.label_texture = label_obj.texture
        min_obj = CoreLabel(text=min_val, font_size=24, font_name=path.join(ASSETS_FONTS_PATH, "Barlow_Condensed", "BarlowCondensed-Bold.ttf"))
        min_obj.refresh()
        self.min_texture = min_obj.texture
        max_obj = CoreLabel(text=max_val, font_size=24, font_name=path.join(ASSETS_FONTS_PATH, "Barlow_Condensed", "BarlowCondensed-Bold.ttf"))
        max_obj.refresh()
        self.max_texture = max_obj.texture
        if icon_source:
            icon_obj = CoreImage(path.join(ASSETS_ICONS_PATH, icon_source))
            self.icon_texture = icon_obj.texture
        else: self.icon_texture = None
        with self.canvas.before:
            self.bg = Rectangle(source=path.join(ASSETS_ICONS_PATH, "guage_bg.png"), pos=self.pos, size=self.size)
        with self.canvas:
            if self.icon_texture: self.icon_rect = Rectangle(texture=self.icon_texture, size=(48, 48), pos=self.pos)
            else: self.icon_rect = None
            self.label_rect = Rectangle(texture=self.label_texture, size=self.label_texture.size, pos=self.pos)
            self.min_rect = Rectangle(texture=self.min_texture, size=self.min_texture.size, pos=self.pos)
            self.max_rect = Rectangle(texture=self.max_texture, size=self.max_texture.size, pos=self.pos)
        with self.canvas.after:
            PushMatrix()
            self.translate = Translate()
            self.rot = Rotate()
            self.needle = Rectangle(source=path.join(ASSETS_ICONS_PATH, "blue_needle_cleaned.png"), pos=self.pos, size=self.size)
            PopMatrix()
        self.bind(pos=self.update_graphics, size=self.update_graphics, angle=self.update_graphics)
    def update_graphics(self, *args):
        cx, cy = self.center
        w, h = self.size
        self.bg.pos = self.pos
        self.bg.size = self.size
        self.needle.size = self.size
        self.needle.pos = (cx - w / 2, cy - h / 2 - 10)
        self.rot.origin = (cx, cy - 66)
        self.rot.angle = self.angle
        self.label_rect.pos = (cx - self.label_texture.size[0] / 2 + 36, self.top - 110)
        self.min_rect.pos = (self.x + 20, self.y + 76)
        self.max_rect.pos = (self.right - self.max_texture.size[0] - 20, self.y + 80)
        if self.icon_rect: self.icon_rect.pos = (cx - 32, self.top - 120)

class RPMBar(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="horizontal", **kwargs)
        self.padding = (15, 0, 0, 0)
        self.spacing = 0
        self.redline_rpm  = 6000
        self._blink_ev    = None
        self._blink_state = True
        with self.canvas.before:
            self.bg_texture = CoreImage(path.join(ASSETS_ICONS_PATH, "gradient_bar.png")).texture
            self.bg_rect = Rectangle(texture=self.bg_texture, pos=self.pos, size=self.size)
            Color(0, 0, 0, 1)
            self.mask_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_geometry, size=self._update_geometry)
        self.label = Label(text="6300", font_size=56, halign="left", valign="middle", width=160, size_hint=(None, 1), font_name=path.join(ASSETS_FONTS_PATH, "Michroma", "Michroma-Regular.ttf"))
        self.label.bind(texture_size=lambda inst, s: setattr(inst, "width", max(160, s[0])))
        self.add_widget(self.label)
        Clock.schedule_interval(self._refresh, 1 / 60) 
    def _update_geometry(self, *_):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
    def _refresh(self, _dt):
        try:
            entry = DATA[PID.RPM]
            rpm_val = float(entry["value"])
            rpm_min, rpm_max = 0, 6300
            rpm_val = max(rpm_min, min(rpm_val, rpm_max))
            self.label.text = f"{round(rpm_val)}"
            frac = (rpm_val - rpm_min) / (rpm_max - rpm_min) if rpm_max != rpm_min else 0
            frac = max(0.0, min(frac, 1.0))
            mask_width = self.width * (1.0 - frac)
            self.mask_rect.size = (mask_width, self.height)
            self.mask_rect.pos = (self.x + self.width - mask_width, self.y)
            self._handle_redline_blink(rpm_val)
        except KeyError:
            self.label.text = "N/A"
            self.mask_rect.size = (self.width, self.height)
    def _handle_redline_blink(self, rpm_val):
        if rpm_val >= self.redline_rpm:
            if self._blink_ev is None: self._blink_ev = Clock.schedule_interval(self._toggle_blink, 0.15)
        else:
            if self._blink_ev is not None:
                self._blink_ev.cancel()
                self._blink_ev = None
                self.opacity = 1
    def _toggle_blink(self, _dt):
        self._blink_state = not self._blink_state
        self.opacity = 1 if self._blink_state else 0

class WarningBox(BoxLayout):
    def __init__(self, title, icon_source, message, assist, **kwargs):
        super().__init__(orientation="vertical", padding=(1), **kwargs)
        self.assist = assist
        self.size_hint = (None, None)
        self.icon = Image(source=path.join(ASSETS_ICONS_PATH, icon_source), size_hint=(None, None), size=(64, 64), pos_hint={"center_x": 0.5})
        self.add_widget(self.icon)
        self.label = Label(text=message, font_size=18, halign="center", valign="middle", size_hint=(1, 1), font_name=path.join(ASSETS_FONTS_PATH, "Barlow_Condensed", "BarlowCondensed-Regular.ttf"))
        self.label.bind(size=self._update_text_size)
        self.add_widget(self.label)
        Clock.schedule_interval(self._refresh, 2)
    def _update_text_size(self, instance, size): instance.text_size = size
    def _refresh(self, _dt):
        message = DRIVER_ASSISTS_STATE[self.assist]["value"]
        show = DRIVER_ASSISTS_STATE[self.assist]["show"]
        self.label.text = message
        self.opacity = 1 if show else 0
        self.disabled = not show

class GaugeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        window_size = Window.size
        self.size = window_size
        root = BoxLayout(orientation="vertical", size=self.size)
        # Fix: Remove fixed rows to allow expansion, though size_hint=(None, None) usually needs explicit sizing or ScrollView.
        # Given it's a dashboard, we might want to keep it fixed but allow more rows if needed.
        # Changing rows to None (default) or automatic based on children.
        gauges_layout = GridLayout(cols=3, spacing=0, size_hint=(None, None), width=960, height=490, pos_hint={"center_x": 0.5})
        header_layout = BoxLayout(orientation="horizontal", size_hint=(1, None), height=100)
        with header_layout.canvas.before:
            Color(0, 0, 0, 1)
            self.bg_rect = Rectangle(size=header_layout.size, pos=header_layout.pos)
            def update_rect(*_):
                self.bg_rect.size = header_layout.size
                self.bg_rect.pos = header_layout.pos
            header_layout.bind(pos=update_rect, size=update_rect)
        warnings_layout = BoxLayout(size_hint=(None, 1), width=120 * len(WARNINGS_TO_SHOW), spacing=10, padding=5)
        for w in WARNINGS_TO_SHOW:
            entry = DRIVER_ASSISTS_STATE[w]
            warning_box = WarningBox(entry["name"], icon_source=entry["icon"], message=entry["value"], assist=w)
            warnings_layout.add_widget(warning_box)
        
        # RPM Bar (Conditional)
        self.rpm_bar = RPMBar(size_hint=(1, 1))
        
        # Settings Button
        settings_btn = Button(text="CONFIG", size_hint=(None, 1), width=80, background_color=(0.2, 0.2, 0.2, 1))
        settings_btn.bind(on_release=self.go_to_settings)
        
        header_layout.add_widget(warnings_layout)
        
        if config_manager.get("show_rpm_bar", True):
             header_layout.add_widget(self.rpm_bar)
             
        header_layout.add_widget(settings_btn)
        
        self.header_layout = header_layout # Keep ref
        
        self.gauges = []
        self.pid_to_gauge = {}
        for pid in GAUGES_TO_SHOW:
            entry = DATA[pid]
            gauge = GaugeWidget(entry["unit"], entry["icon"], str(entry["dial_min"]), str(entry["dial_max"]))
            self.pid_to_gauge[pid] = gauge
            self.gauges.append(gauge)
            gauges_layout.add_widget(gauge)
        root.add_widget(header_layout)
        root.add_widget(gauges_layout)
        self.add_widget(root)
        
        self.gauges_layout = gauges_layout # Keep reference for rebuild
        
        Clock.schedule_interval(self.update_all_gauges, GAUGE_UPDATE_INTERVAL)
        
    def rebuild_ui(self):
        print("[*] GaugeScreen: Rebuilding UI...")
        self.gauges_layout.clear_widgets()
        self.gauges = []
        self.pid_to_gauge = {}
        
        # Reload keys
        # Reload keys
        global GAUGES_TO_SHOW, WARNINGS_TO_SHOW
        keys = config_manager.get("gauges")
        # Safety: Truncate to MAX_GAUGES to prevent crash
        if len(keys) > MAX_GAUGES:
             print(f"[!] Warning: Config has {len(keys)} gauges. Truncating to {MAX_GAUGES}.")
             keys = keys[:MAX_GAUGES]
             
        GAUGES_TO_SHOW = [getattr(PID, k) for k in keys if hasattr(PID, k)]
        
        w_keys = config_manager.get("warnings")
        WARNINGS_TO_SHOW = [getattr(AssistKey, k) for k in w_keys if hasattr(AssistKey, k)]
        
        # Rebuild Header (Warnings + RPM Bar)
        self.header_layout.clear_widgets()
        
        warnings_layout = BoxLayout(size_hint=(None, 1), width=120 * len(WARNINGS_TO_SHOW), spacing=10, padding=5)
        for w in WARNINGS_TO_SHOW:
               entry = DRIVER_ASSISTS_STATE[w]
               warning_box = WarningBox(entry["name"], icon_source=entry["icon"], message=entry["value"], assist=w)
               warnings_layout.add_widget(warning_box)
        
        settings_btn = Button(text="CONFIG", size_hint=(None, 1), width=80, background_color=(0.2, 0.2, 0.2, 1))
        settings_btn.bind(on_release=self.go_to_settings)

        self.header_layout.add_widget(warnings_layout)
        if config_manager.get("show_rpm_bar", True):
            self.header_layout.add_widget(self.rpm_bar)
        self.header_layout.add_widget(settings_btn)

        
        for pid in GAUGES_TO_SHOW:
            entry = DATA[pid]
            gauge = GaugeWidget(entry["unit"], entry["icon"], str(entry["dial_min"]), str(entry["dial_max"]))
            self.pid_to_gauge[pid] = gauge
            self.gauges.append(gauge)
            self.gauges_layout.add_widget(gauge)

    def update_all_gauges(self, dt):
        for pid, gauge in self.pid_to_gauge.items(): self.update_gauge(pid, gauge)
    
    def go_to_settings(self, *args):
        self.parent.current = 'settings'
        self.parent.transition.direction = 'left'

    def update_gauge(self, pid, gauge):
        entry = DATA[pid]
        val = float(entry["value"])
        min_d = entry["dial_min"]
        max_d = entry["dial_max"]
        val = max(min_d, min(val, max_d))
        target_angle = DIAL_MIN + ((val - min_d) / (max_d - min_d)) * (DIAL_MAX - DIAL_MIN)
        if not hasattr(gauge, '_target_angle'): gauge._target_angle = None
        if gauge._target_angle is None or abs(gauge._target_angle - target_angle) > 0.5:
            gauge._target_angle = target_angle
            Animation.cancel_all(gauge, 'angle')
            anim = Animation(angle=target_angle, duration=0.15, t='out_quad')
            anim.start(gauge)

class DigitalScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        grid = GridLayout(cols=3, rows=2, padding=25, spacing=0)
        self.pid_to_cell = {}
        for idx, pid in enumerate(DATACELLS_TO_SHOW):
            info = DATA[pid]
            row = idx // 3
            col = idx % 3
            draw_top = row != 0
            draw_left = col != 0
            cell = DataCell(f'{info["name"]} ({info["unit"]})', info["value"], info["min_read"], info["max_read"], draw_top=draw_top, draw_left=draw_left)
            self.pid_to_cell[pid] = cell
            grid.add_widget(cell)
        self.add_widget(grid)
        self.grid = grid # Keep reference
        Clock.schedule_interval(self.update_all_cells, GAUGE_UPDATE_INTERVAL)  

    def rebuild_ui(self):
        print("[*] DigitalScreen: Rebuilding UI...")
        self.grid.clear_widgets()
        self.pid_to_cell = {}
        
        # Reload keys
        global DATACELLS_TO_SHOW
        keys = config_manager.get("datacells")
        DATACELLS_TO_SHOW = [getattr(PID, k) for k in keys if hasattr(PID, k)]
        
        for idx, pid in enumerate(DATACELLS_TO_SHOW):
            info = DATA[pid]
            row = idx // 3
            col = idx % 3
            draw_top = row != 0
            draw_left = col != 0
            cell = DataCell(f'{info["name"]} ({info["unit"]})', info["value"], info["min_read"], info["max_read"], draw_top=draw_top, draw_left=draw_left)
            self.pid_to_cell[pid] = cell
            self.grid.add_widget(cell)

    def update_all_cells(self, dt):
        global DATA
        for pid, cell in self.pid_to_cell.items():
            entry = DATA[pid]
            val = float(entry["value"])
            min_ = float(entry["min_read"])
            max_ = float(entry["max_read"])
            cell.update_readings(val, min_, max_)
        
class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Header
        header = BoxLayout(size_hint=(1, None), height=50)
        header.add_widget(Label(text="Settings", font_size=32, bold=True))
        back_btn = Button(text="Back", size_hint=(None, 1), width=100)
        back_btn.bind(on_release=self.go_back)
        header.add_widget(back_btn)
        self.layout.add_widget(header)

        # Scrollable Content
        scroll = ScrollView()
        content = GridLayout(cols=1, spacing=10, size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))

        # 1. Configurable Gauges
        self.gauge_toggles = {}
        gauges_grid = GridLayout(cols=3, spacing=5, size_hint_y=None)
        gauges_grid.bind(minimum_height=gauges_grid.setter('height'))
        
        current_gauges = config_manager.get("gauges")
        for pid_name in PID.__members__:
            box = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
            chk = CheckBox(active=(pid_name in current_gauges))
            box.add_widget(chk)
            box.add_widget(Label(text=pid_name))
            box.add_widget(Label(text=pid_name))
            chk.bind(active=self.on_gauge_toggle)
            self.gauge_toggles[pid_name] = chk
            gauges_grid.add_widget(box)
        content.add_widget(gauges_grid)
        
        # Enforce initial state
        self.update_gauge_locks()

        # 2. Configurable DataCells
        content.add_widget(Label(text="Active Digital Cells", size_hint_y=None, height=40, font_size=24))
        self.datacell_toggles = {}
        datacell_grid = GridLayout(cols=3, spacing=5, size_hint_y=None)
        datacell_grid.bind(minimum_height=datacell_grid.setter('height'))
        
        current_datacells = config_manager.get("datacells")
        for pid_name in PID.__members__:
            box = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
            chk = CheckBox(active=(pid_name in current_datacells))
            box.add_widget(chk)
            box.add_widget(Label(text=pid_name))
            self.datacell_toggles[pid_name] = chk
            datacell_grid.add_widget(box)
        content.add_widget(datacell_grid)

        # 3. Driver Assists
        content.add_widget(Label(text="Active Assists/Warnings", size_hint_y=None, height=40, font_size=24))
        self.assist_toggles = {}
        assist_grid = GridLayout(cols=2, spacing=5, size_hint_y=None)
        assist_grid.bind(minimum_height=assist_grid.setter('height'))
        
        current_warnings = config_manager.get("warnings")
        for assist_key in AssistKey.__members__:
            box = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
            chk = CheckBox(active=(assist_key in current_warnings))
            box.add_widget(chk)
            box.add_widget(Label(text=assist_key))
            self.assist_toggles[assist_key] = chk
            assist_grid.add_widget(box)
        content.add_widget(assist_grid)

        # 4. General Settings
        content.add_widget(Label(text="General", size_hint_y=None, height=40, font_size=24))
        
        # RPM Bar
        rpm_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        self.rpm_bar_chk = CheckBox(active=config_manager.get("show_rpm_bar", True))
        rpm_box.add_widget(self.rpm_bar_chk)
        rpm_box.add_widget(Label(text="Show RPM Bar"))
        content.add_widget(rpm_box)

        # Redline
        content.add_widget(Label(text="Redline RPM", size_hint_y=None, height=40))
        self.redline_input = TextInput(text=str(config_manager.get("redline")), multiline=False, size_hint_y=None, height=40)
        content.add_widget(self.redline_input)
        
        # Save Button
        save_btn = Button(text="Save & Restart", size_hint_y=None, height=60, background_color=(0, 1, 0, 1))
        save_btn.bind(on_release=self.save_config)
        content.add_widget(save_btn)

        scroll.add_widget(content)
        self.layout.add_widget(scroll)
        self.add_widget(self.layout)

    def on_gauge_toggle(self, instance, value):
        self.update_gauge_locks()
        
    def update_gauge_locks(self):
        active_count = sum(1 for chk in self.gauge_toggles.values() if chk.active)
        
        disable_others = active_count >= MAX_GAUGES
        
        for chk in self.gauge_toggles.values():
            if not chk.active:
                chk.disabled = disable_others
                chk.opacity = 0.5 if disable_others else 1.0

    def go_back(self, *args):
        self.manager.current = 'gauge'
        self.manager.transition.direction = 'right'

    def save_config(self, *args):
        # Update Gauges
        new_gauges = [k for k, v in self.gauge_toggles.items() if v.active]
        config_manager.set("gauges", new_gauges)
        
        # Update DataCells
        new_datacells = [k for k, v in self.datacell_toggles.items() if v.active]
        config_manager.set("datacells", new_datacells)
        
        # Update Warnings/Assists
        new_warnings = [k for k, v in self.assist_toggles.items() if v.active]
        config_manager.set("warnings", new_warnings)
        
        # Update RPM Bar
        config_manager.set("show_rpm_bar", self.rpm_bar_chk.active)
        
        # Update Redline
        try:
            new_redline = int(self.redline_input.text)
            config_manager.set("redline", new_redline)
        except ValueError:
            pass
            
        # Show Popup
        popup = Popup(title='Saved',
                      content=Label(text='Settings saved!\nPlease restart the app.'),
                      size_hint=(None, None), size=(400, 200))
        popup.open()

class RootWidget(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(transition=SlideTransition(duration=0.4), **kwargs)
        self.add_widget(GaugeScreen(name='gauge'))
        self.add_widget(DigitalScreen(name='digital'))
        self.add_widget(SettingsScreen(name='settings'))
        self.current = 'gauge'
    def on_touch_move(self, touch):
        # Disabled swipe for settings to avoid accidental confusion
        if self.current == 'settings': return
        
        if touch.dx < -40: self.switch_to_screen('digital')
        elif touch.dx > 40: self.switch_to_screen('gauge')
    def switch_to_screen(self, name):
        if self.current != name:
            self.transition.direction = 'left' if name == 'digital' else 'right'
            self.current = name

class DashApp(App):
    def build(self):
        self.root_widget = RootWidget()
        Clock.schedule_interval(self.check_config_updates, 1.0)
        return self.root_widget
        
    def on_start(self): 
        threading.Thread(target=start_obd_polling, daemon=True).start()
        
    def check_config_updates(self, dt):
        if config_manager.check_for_changes():
            print("[*] App: Detected config change. Triggering UI Rebuild.")
            # Trigger rebuild on screens
            gauge_scr = self.root_widget.get_screen('gauge')
            if hasattr(gauge_scr, 'rebuild_ui'): gauge_scr.rebuild_ui()
            
            digit_scr = self.root_widget.get_screen('digital')
            if hasattr(digit_scr, 'rebuild_ui'): digit_scr.rebuild_ui()

if __name__ == '__main__':
    DashApp().run()