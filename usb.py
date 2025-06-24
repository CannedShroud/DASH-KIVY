from kivy.config import Config
Config.set("graphics", "fullscreen", "auto")
Config.set('graphics', 'show_cursor', '0')

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.config import Config
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.uix.gridlayout import GridLayout
from kivy.graphics import Color, Line
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Rectangle, Rotate, PushMatrix, PopMatrix, Translate
from kivy.properties import NumericProperty
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.text import Label as CoreLabel
from kivy.animation import Animation
import threading
import subprocess
import re
import time
from math import inf
import math 
import random

# Fullscreen, no borders, hide mouse
Config.set('graphics', 'fullscreen', 'auto')
Window.show_cursor = False

DIAL_MIN = 18
DIAL_MAX = -110

GAUGE_UPDATE_INTERVAL = 0.2

CANUSB_BIN = "./canusb"
DEVICE = "/dev/ttyUSB0"
CAN_SPEED = "500000"
REQUEST_INTERVAL = 0  # seconds

OBD_REQ_ID = "7DF"

DATA = {
    "0B": {
        "name": "Boost",
        "unit": "psi",
        "convert": lambda A: A * 0.145,
        "bytes": 1,
        "dial_min": -20,
        "dial_max": 20,
        "value": 0,
        "min_read": inf,
        "max_read": -inf,
        "icon": "./boost_pressure.png",
        "precision": 2
    },
    "0F": {
        "name": "Intake Air Temp",
        "unit": "°C",
        "convert": lambda A: A - 40,
        "bytes": 1,
        "dial_min": 0,
        "dial_max": 80,
        "value": 40,
        "min_read": inf,
        "max_read": -inf,
        "icon": "./iat.png",
        "precision": 0
    },
    "05": {
        "name": "Coolant Temp",
        "unit": "°C",
        "convert": lambda A: A - 40,
        "bytes": 1,
        "dial_min": 40,
        "dial_max": 120,
        "value": 90,
        "min_read": inf,
        "max_read": -inf,
        "icon": "./coolant_temp.png",
        "precision": 0
    },
    "5C": {
        "name": "Oil Temp",
        "unit": "°C",
        "convert": lambda A: A - 40,
        "bytes": 1,
        "dial_min": 40,
        "dial_max": 150,
        "value": 100,
        "min_read": inf,
        "max_read": -inf,
        "icon": "./oil_temp.png",
        "precision": 0
    },
    "3C": {
        "name": "EGT",
        "unit": "°C",
        "convert": lambda A, B: ((A * 256 + B) / 10) - 40,
        "bytes": 2,
        "dial_min": 200,
        "dial_max": 1000,
        "value": 600,
        "min_read": inf,
        "max_read": -inf,
        "icon": "./egt.png",
        "precision": 0
    },
    "42": {
        "name": "Voltage",
        "unit": "V",
        "convert": lambda A: A / 10.0,
        "bytes": 1,
        "dial_min": 10,
        "dial_max": 15,
        "value": 13.8,
        "min_read": inf,
        "max_read": -inf,
        "icon": "./battery.png",
        "precision": 1
    },
}

FRAME_RE = re.compile(r"Frame ID:\s*([0-9A-Fa-f]+),\s*Data:\s*([0-9A-Fa-f ]+)")

def dummy_thread():
    t = 0
    while True:
        # print("Simulating.")
        for pid, entry in DATA.items():
            try:
                dial_min = entry["dial_min"]
                dial_max = entry["dial_max"]

                amplitude = (dial_max - dial_min) / 2
                center = (dial_max + dial_min) / 2
                noise = random.uniform(-1, 1)

                # Simulate value
                if pid == "0B":  # Boost
                    value = center + amplitude * math.sin(t * 1.5) + noise * 2
                    value = max(dial_min, min(dial_max, value))
                    A = int(value + 1)  # A = psi (simplified inverse)
                    frame = f"03 41 {pid} {A:02X} 00 00 00 00"

                elif pid == "0F":  # Intake Air Temp (IAT = A - 40)
                    value = center + amplitude * math.sin(t * 0.2) + noise
                    value = max(dial_min, min(dial_max, value))
                    A = int(value + 40)
                    frame = f"03 41 {pid} {A:02X} 00 00 00 00"

                elif pid == "05":  # Coolant Temp (Temp = A - 40)
                    value = center + amplitude * math.sin(t * 0.1) + noise
                    value = max(dial_min, min(dial_max, value))
                    A = int(value + 40)
                    frame = f"03 41 {pid} {A:02X} 00 00 00 00"

                elif pid == "5C":  # Oil Temp (same as IAT)
                    value = center + amplitude * math.sin(t * 0.1) + noise
                    value = max(dial_min, min(dial_max, value))
                    A = int(value + 40)
                    frame = f"03 41 {pid} {A:02X} 00 00 00 00"

                elif pid == "3C":  # EGT (val = (A*256 + B)/10)
                    value = center + amplitude * math.sin(t * 1.2 + random.uniform(-0.2, 0.2)) + noise * 5
                    value = max(dial_min, min(dial_max, value))
                    raw = int(value * 10)
                    A = (raw >> 8) & 0xFF
                    B = raw & 0xFF
                    frame = f"03 41 {pid} {A:02X} {B:02X} 00 00 00"

                elif pid == "42":  # Voltage (A / 10)
                    value = center + math.sin(t * 0.1) * 0.1 + noise * 0.05
                    value = max(dial_min, min(dial_max, value))
                    A = int(value * 10)
                    frame = f"03 41 {pid} {A:02X} 00 00 00 00"

                else:  # Generic 1-byte
                    value = center + amplitude * math.sin(t)
                    value = max(dial_min, min(dial_max, value))
                    A = int(value)
                    frame = f"03 41 {pid} {A:02X} 00 00 00 00"

                reversed_bytes = list(reversed(frame.split()))
                reversed_frame_str = " ".join(reversed_bytes)
                # decode_frame(reversed_frame_str)

            except Exception as e:
                print(f"[!] Error simulating {pid}: {e}")

        t += 0.1
        time.sleep(0.2)

def decode_frame(data_str):
    # print(f"[decode_frame] Received frame: {data_str}")
    global DATA

    bytes_list = list(reversed(data_str.strip().split()))
    # print(f"[decode_frame] Reversed byte list: {bytes_list}")

    if len(bytes_list) < 4:
        # print("[decode_frame] Frame too short, skipping.")
        return None

    try:
        mode = bytes_list[1].upper()
        pid = bytes_list[2].upper()
        # print(f"[decode_frame] Mode: {mode}, PID: {pid}")

        if mode != "41":
            # print(f"[decode_frame] Unexpected mode: {mode}, ignoring.")
            return None

        entry = DATA.get(pid)
        if not entry:
            # print(f"[decode_frame] PID {pid} not found in DATA.")
            return None

        if entry["bytes"] == 2:
            A = int(bytes_list[3], 16)
            B = int(bytes_list[4], 16)
            # print(f"[decode_frame] Parsed A: {A}, B: {B}")
            value = entry["convert"](A, B)
        elif entry["bytes"] == 1:
            A = int(bytes_list[3], 16)
            # print(f"[decode_frame] Parsed A: {A}")
            value = entry["convert"](A)
        else:
            # print(f"[decode_frame] Unsupported byte size for PID {pid}")
            return None

        # print(f"[decode_frame] Computed value: {value}")

        DATA[pid]["value"] = str(f"{float(value):.{DATA[pid]['precision']}f}")
        DATA[pid]["min_read"] = str(min(float(DATA[pid]["min_read"]), float(value)))
        DATA[pid]["max_read"] = str(max(float(DATA[pid]["max_read"]), float(value)))

        # print(f"[decode_frame] Updated DATA[{pid}]: value={DATA[pid]['value']}, "
              # f"min_read={DATA[pid]['min_read']}, max_read={DATA[pid]['max_read']}")
        for pid, p in DATA.items():
            print(f"{p['name']} ({pid}): {p['value']}")


    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[!] Decode error for PID {pid}: {e}")
        return None


def send_obd_requests():
    global DATA
    print("[*] OBD request thread started")
    for pid in DATA:
        data = f"0201{pid}0000000000"
        try:
            # print(f"[>] trying to request PID {pid}")
            subprocess.Popen(
                [CANUSB_BIN, "-d", DEVICE, "-s", CAN_SPEED, "-i", OBD_REQ_ID, "-j", data, "-g", "100"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # print(f"[>] Sent request for PID {pid}")
            time.sleep(0.3)  # slight gap between requests
        except Exception as e:
            import traceback
            traceback.print_exc()

            print(f"[!] Error sending request for PID {pid}: {e}")
        # time.sleep(REQUEST_INTERVAL)



def start_obd_listener():
    print("[*] Starting CANUSB monitor...")

    try:
        # Start monitor process
        print(f"[DEBUG] Launching: stdbuf -oL {CANUSB_BIN} -t -d {DEVICE} -s {CAN_SPEED}")
        monitor_proc = subprocess.Popen(
            ["stdbuf", "-oL", CANUSB_BIN, "-t", "-d", DEVICE, "-s", CAN_SPEED],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,  # changed to PIPE to capture errors
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        print(" ".join(["stdbuf", "-oL", CANUSB_BIN, "-t", "-d", DEVICE, "-s", CAN_SPEED]))

        if monitor_proc.stdout is None:
            print("[ERROR] monitor_proc.stdout is None. Subprocess may have failed.")
            stderr_output = monitor_proc.stderr.read()
            print(f"[STDERR OUTPUT]: {stderr_output}")
            return

        print("[*] CANUSB monitor launched successfully.")
        print("[*] Reading from CANUSB...")

        while True:
            print("[DEBUG] Waiting for next line from CANUSB...")
            line = monitor_proc.stdout.readline()
            print(f"[DEBUG] Received line: {line.strip()}")

            if not line:
                # print("[WARNING] Empty line received. Continuing...")
                continue

            match = FRAME_RE.search(line)
            if match:
                frame_id = match.group(1).upper()
                data = match.group(2).strip()
                print(f"[DEBUG] Matched frame_id: {frame_id}, data: {data}")
                decode_frame(data)
            else:
                pass
                # print(f"[WARNING] Line did not match expected format: {line.strip()}")

            time.sleep(0.3)

    except Exception as e:
        print("[!] Exception occurred in start_obd_listener()")
        import traceback
        traceback.print_exc()

class DataCell(BoxLayout):
    def __init__(self, title, value, min_val, max_val, draw_top=False, draw_left=False, **kwargs):
        super().__init__(orientation='vertical', padding=5, **kwargs)

        self.draw_top = draw_top
        self.draw_left = draw_left

        self.title = Label(text=title, font_size='28sp', font_name="./Barlow_Condensed/BarlowCondensed-Regular.ttf")
        self.value = Label(text=str(value), font_size='72sp', bold=True, font_name="./Michroma/Michroma-Regular.ttf",)
        self.min_val = Label(text=str(min_val), font_size='28sp', font_name="./Barlow_Condensed/BarlowCondensed-Bold.ttf",)
        self.separator = Label(text="|", font_size='28sp', font_name="./Barlow_Condensed/BarlowCondensed-Bold.ttf",)
        self.max_val = Label(text=str(max_val), font_size='28sp', font_name="./Barlow_Condensed/BarlowCondensed-Bold.ttf",)

        readings_box = BoxLayout(orientation='horizontal', spacing=0, size_hint=(None, None), pos_hint={'center_x': 0.5, 'center_y': 0.5})


        # Add the widgets to the horizontal layout
        readings_box.add_widget(self.min_val)
        readings_box.add_widget(self.separator)
        readings_box.add_widget(self.max_val)

        self.add_widget(self.title)
        self.add_widget(self.value)
        self.add_widget(readings_box)

        with self.canvas.after:
            Color(0.7, 0.7, 0.7, 1)  # Gray

            if self.draw_top:
                self.top_line = Line(points=[self.x, self.top, self.right, self.top], width=1)
            if self.draw_left:
                self.left_line = Line(points=[self.x, self.y, self.x, self.top], width=1)

        self.bind(pos=self.update_lines, size=self.update_lines)

    def update_lines(self, *args):
        if hasattr(self, 'top_line'):
            self.top_line.points = [self.x, self.top, self.right, self.top]
        if hasattr(self, 'left_line'):
            self.left_line.points = [self.x, self.y, self.x, self.top]

    def update_readings(self, value, min_read, max_read):
        self.value.text = str(value)
        self.min_val.text = str(min_read)
        self.max_val.text = str(max_read)


class GaugeWidget(Widget):
    angle = NumericProperty(0)

    def __init__(self, label="RPM", icon_source=None, min_val="0", max_val="8000", **kwargs):
        super().__init__(**kwargs)

        self.size = (320, 240)
        self.size_hint = (None, None)

        self.label_text = label
        self.icon_source = icon_source
        self.min_val = min_val
        self.max_val = max_val

        # Label texture
        label_obj = CoreLabel(text=label, font_size=24, bold=True)
        label_obj.refresh()
        self.label_texture = label_obj.texture

        # Min value texture
        min_obj = CoreLabel(text=min_val, font_size=24, font_name="./Barlow_Condensed/BarlowCondensed-Bold.ttf")
        min_obj.refresh()
        self.min_texture = min_obj.texture

        # Max value texture
        max_obj = CoreLabel(text=max_val, font_size=24, font_name="./Barlow_Condensed/BarlowCondensed-Bold.ttf")
        max_obj.refresh()
        self.max_texture = max_obj.texture

        # Icon texture (if provided)
        if icon_source:
            icon_obj = CoreImage(icon_source)
            self.icon_texture = icon_obj.texture
        else:
            self.icon_texture = None

        with self.canvas.before:
            # Gauge background
            self.bg = Rectangle(source="guage_bg.png", pos=self.pos, size=self.size)

        with self.canvas:
            if self.icon_texture:
                self.icon_rect = Rectangle(texture=self.icon_texture, size=(48, 48), pos=self.pos)
            else:
                self.icon_rect = None

            # Label and value markers
            self.label_rect = Rectangle(texture=self.label_texture, size=self.label_texture.size, pos=self.pos)
            self.min_rect = Rectangle(texture=self.min_texture, size=self.min_texture.size, pos=self.pos)
            self.max_rect = Rectangle(texture=self.max_texture, size=self.max_texture.size, pos=self.pos)
        with self.canvas.after:
            # Rotating needle
            PushMatrix()
            self.translate = Translate()
            self.rot = Rotate()
            self.needle = Rectangle(source="blue_needle_cleaned.png", pos=self.pos, size=self.size)
            PopMatrix()


        self.bind(pos=self.update_graphics, size=self.update_graphics, angle=self.update_graphics)

    def update_graphics(self, *args):
        cx, cy = self.center
        w, h = self.size

        # Gauge background
        self.bg.pos = self.pos
        self.bg.size = self.size

        # Needle rotation
        self.needle.size = self.size
        self.needle.pos = (cx - w / 2, cy - h / 2 - 10)
        self.rot.origin = (cx, cy - 70)
        self.rot.angle = self.angle

        # Title label (centered above)
        self.label_rect.pos = (cx - self.label_texture.size[0] / 2 + 36, self.top - 110)

        # Min and max labels
        self.min_rect.pos = (self.x + 20, self.y + 76)
        self.max_rect.pos = (self.right - self.max_texture.size[0] - 20, self.y + 80)

        # Icon
        if self.icon_rect:
            self.icon_rect.pos = (cx - 32, self.top - 120)

    def update_reading(self, val, min_read, max_read):
        mapped_value = DIAL_MIN + ((val - min_read) / (max_read - min_read)) * (DIAL_MAX - DIAL_MIN)
        while self.rot.angle < mapped_value:
            self.rot.angle += 6            
        while self.rot.angle > mapped_value:
            self.rot.angle -= 6

class GaugeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = GridLayout(cols=3, rows=2, padding=25, spacing=0)

        self.gauges = []
        self.pid_to_gauge = {}

        for pid, entry in DATA.items():
            gauge = GaugeWidget(entry["unit"], entry["icon"], str(entry["dial_min"]), str(entry["dial_max"]))
            self.pid_to_gauge[pid] = gauge
            self.gauges.append(gauge)
            layout.add_widget(gauge)

        self.add_widget(layout)
        # Clock.schedule_once(self.run_initial_sweep, 0.5)
        Clock.schedule_interval(self.update_all_gauges, GAUGE_UPDATE_INTERVAL)
        # Clock.schedule_interval(update, 1 / 120)

    def update_all_gauges(self, dt):
        for pid, gauge in self.pid_to_gauge.items():
                self.update_gauge(pid, gauge)

    def update_gauge(self, pid, gauge):
        entry = DATA[pid]
        val = float(entry["value"])
        min_d = entry["dial_min"]
        max_d = entry["dial_max"]

        # Clamp value
        val = max(min_d, min(val, max_d))

        # Target angle
        target_angle = DIAL_MIN + ((val - min_d) / (max_d - min_d)) * (DIAL_MAX - DIAL_MIN)

        # Animate angle smoothly over 0.3 seconds
        Animation.cancel_all(gauge, 'angle')  # cancel any existing animation on this property
        anim = Animation(angle=target_angle, duration=0.3, t='out_quad')
        anim.start(gauge)


    # def run_initial_sweep(self, dt):
    #     for gauge in self.gauges:
    #         self.animate_sweep(gauge)

    # def animate_sweep(self, gauge):
    #     direction = [1]
    #
    #     def update(dt):
    #         if direction[0] == 1:
    #             if gauge.angle > DIAL_MAX:
    #                 gauge.angle -= 3
    #             else:
    #                 direction[0] = -1
    #         elif direction[0] == -1:
    #             if gauge.angle < DIAL_MIN:
    #                 gauge.angle += 3
    #             else: 
    #                 return False
    #
    #         return True
    #
    #     Clock.schedule_interval(update, 1/360)

class GaugeContainer(BoxLayout):
    def __init__(self, label="RPM", icon_source="rpm_icon.png", min_val="0", max_val="8000", **kwargs):
        super().__init__(orientation="vertical", spacing=4, padding=4, **kwargs)
        self.size_hint = (None, None)
        self.size = (320, 240)

        # Icon
        self.icon = Image(source=icon_source, size_hint=(None, None), size=(32, 32))
        self.icon.opacity = 1
        self.icon.allow_stretch = True
        self.icon.keep_ratio = True
        self.icon.pos_hint = {"center_x": 0.5}
        self.add_widget(self.icon)

        # Gauge widget
        self.gauge = GaugeWidget()
        self.add_widget(self.gauge)

        # Label below
        self.label = Label(text=label, font_size=16, bold=True, halign="center", size_hint_y=None, height=24)
        self.add_widget(self.label)

        # Min/Max
        minmax = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=5, padding=[10, 0])

        min_label = Label(
            text=min_val,
            font_size=32,
            size_hint_x=0.5,
            halign="left",
            valign="middle"
        )
        min_label.bind(size=lambda instance, value: setattr(instance, 'text_size', value))

        max_label = Label(
            text=max_val,
            font_size=32,
            size_hint_x=0.5,
            halign="right",
            valign="middle"
        )
        max_label.bind(size=lambda instance, value: setattr(instance, 'text_size', value))

        minmax.add_widget(min_label)
        minmax.add_widget(max_label)
        self.add_widget(minmax)

class DigitalScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        grid = GridLayout(cols=3, rows=2, padding=25, spacing=0)

        self.pid_to_cell = {}

        for idx, (pid, info) in enumerate(DATA.items()):
            row = idx // 3
            col = idx % 3
            draw_top = row != 0
            draw_left = col != 0
            cell = DataCell(f'{info["name"]} ({info["unit"]})', info["value"], info["min_read"], info["max_read"], draw_top=draw_top, draw_left=draw_left)
            self.pid_to_cell[pid] = cell
            grid.add_widget(cell)

        self.add_widget(grid)

        Clock.schedule_interval(self.update_all_cells, GAUGE_UPDATE_INTERVAL)  

    def update_all_cells(self, dt):
        global DATA
        for pid, cell in self.pid_to_cell.items():
            entry = DATA[pid]
            val = float(entry["value"])
            min_ = float(entry["min_read"])
            max_ = float(entry["max_read"])
            cell.update_readings(val, min_, max_)
        
class RootWidget(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(transition=SlideTransition(duration=0.4), **kwargs)
        self.add_widget(GaugeScreen(name='gauge'))
        self.add_widget(DigitalScreen(name='digital'))
        self.current = 'gauge'

    def on_touch_move(self, touch):
        if touch.dx < -40:
            self.switch_to_screen('digital')
        elif touch.dx > 40:
            self.switch_to_screen('gauge')

    def switch_to_screen(self, name):
        if self.current != name:
            self.transition.direction = 'left' if name == 'digital' else 'right'
            self.current = name

class DashApp(App):
    def build(self):
        return RootWidget()
    def on_start(self):
        threading.Thread(target=send_obd_requests, daemon=True).start()
        threading.Thread(target=start_obd_listener, daemon=True).start()
        threading.Thread(target=dummy_thread, daemon=True).start()

if __name__ == '__main__':
    DashApp().run()

