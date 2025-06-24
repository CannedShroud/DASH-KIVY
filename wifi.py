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

USE_FAKE_OBD = False
DIAL_MIN = 18
DIAL_MAX = -110
OBD_WIFI_IP = "192.168.0.10"
OBD_WIFI_PORT = 35000
GAUGE_UPDATE_INTERVAL = 0.2
ASSETS_ICONS_PATH = "./assets/icons/"
ASSETS_FONTS_PATH = "./assets/fonts"

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

DATA = {
    PID.BARO: {
        "name": "Barometer",
        "pid": "33",
        "unit": "psi",
        "convert": lambda A: (A * 0.145) - 14.5,
        "obd": obd.commands.BAROMETRIC_PRESSURE,
        "bytes": 1,
        "dial_min": -20,
        "dial_max": 20,
        "value": 0,
        "min_read": inf,
        "max_read": -inf,
        "icon": "boost_pressure.png",
        "precision": 2
    },
    PID.BOOST: {
        "name": "Boost",
        "pid": "0B",
        "unit": "psi",
        "convert": lambda A: (A * 0.145) - 14.5,
        "obd": obd.commands.INTAKE_PRESSURE,
        "bytes": 1,
        "dial_min": -20,
        "dial_max": 20,
        "value": 0,
        "min_read": inf,
        "max_read": -inf,
        "icon": "boost_pressure.png",
        "precision": 2
    },
    PID.IAT: {
        "name": "Intake Air Temp",
        "pid": "0F",
        "unit": "°C",
        "convert": lambda A: A,
        "obd": obd.commands.INTAKE_TEMP,
        "bytes": 1,
        "dial_min": 0,
        "dial_max": 80,
        "value": 40,
        "min_read": inf,
        "max_read": -inf,
        "icon": "iat.png",
        "precision": 0
    },
    PID.AFR: {
        "name": "Commanded AFR",
        "pid": "44",
        "unit": "λ",
        "convert": lambda A: (A * 256) / 32768,
        "obd": obd.commands.COMMANDED_EQUIV_RATIO,
        "bytes": 2,
        "dial_min": 0.7,
        "dial_max": 1.3,
        "value": 1.0,
        "min_read": float('inf'),
        "max_read": float('-inf'),
        "icon": "afr.png",
        "precision": 2
    },
    PID.TIMING: {
        "name": "Timing Advance",
        "pid": "0E",
        "unit": "°",
        "convert": lambda A: (A / 2) - 64,
        "obd": obd.commands.TIMING_ADVANCE,
        "bytes": 1,
        "dial_min": -20,
        "dial_max": 60,
        "value": 0,
        "min_read": float('inf'),
        "max_read": float('-inf'),
        "icon": "timing.png",
        "precision": 0
    },
    PID.COOLANT_TEMP: {
        "name": "Coolant Temp",
        "pid": "05",
        "unit": "°C",
        "convert": lambda A: A,
        "obd": obd.commands.COOLANT_TEMP,
        "bytes": 1,
        "dial_min": 40,
        "dial_max": 120,
        "value": 90,
        "min_read": inf,
        "max_read": -inf,
        "icon": "coolant_temp.png",
        "precision": 0
    },
    PID.OIL_TEMP: {
        "name": "Oil Temp",
        "pid": "5C",
        "unit": "°C",
        "convert": lambda A: A,
        "obd": obd.commands.OIL_TEMP,
        "bytes": 1,
        "dial_min": 40,
        "dial_max": 120,
        "value": 90,
        "min_read": inf,
        "max_read": -inf,
        "icon": "oil_temp.png",
        "precision": 0
    },
    PID.VOLTAGE: {
        "name": "Voltage",
        "pid": "42",
        "unit": "V",
        "convert": lambda A: A / 10.0,
        "obd": obd.commands.CONTROL_MODULE_VOLTAGE,
        "bytes": 1,
        "dial_min": 5,
        "dial_max": 20,
        "value": 12,
        "min_read": inf,
        "max_read": -inf,
        "icon": "battery.png",
        "precision": 1
    },
    PID.RPM: {
        "name": "RPM",
        "pid": "0C",
        "unit": "rpm",
        "convert": lambda A: A,
        "obd": obd.commands.RPM,
        "bytes": 1,
        "dial_min": 0,
        "dial_max": 7000,
        "value": 800,
        "min_read": float('inf'),
        "max_read": float('-inf'),
        "icon": "speedo.png",
        "precision": 0
    },
    PID.THROTTLE: {
        "name": "Throttle",
        "pid": "11",
        "unit": "%",
        "convert": lambda A: A,
        "obd": obd.commands.THROTTLE_POS,
        "bytes": 1,
        "dial_min": 0,
        "dial_max": 100,
        "value": 0,
        "min_read": float('inf'),
        "max_read": float('-inf'),
        "icon": "throttlebody.png",
        "precision": 0
    },
    PID.SPEED: {
        "name": "Speed",
        "pid": "0D",
        "unit": "km/h",
        "convert": lambda A: A,
        "obd": obd.commands.SPEED,
        "bytes": 1,
        "dial_min": 0,
        "dial_max": 180,
        "value": 0,
        "min_read": float('inf'),
        "max_read": float('-inf'),
        "icon": "speedo.png",
        "precision": 0
    },
    PID.LTFT: {
        "name": "LTFT",
        "pid": "07",
        "unit": "%",
        "convert": lambda A: A,
        "obd": obd.commands.LONG_FUEL_TRIM_1,
        "bytes": 1,
        "dial_min": -20,
        "dial_max": 20,
        "value": 0,
        "min_read": float('inf'),
        "max_read": float('-inf'),
        "icon": "trim.png",
        "precision": 1
    },
    PID.STFT: {
        "name": "STFT",
        "pid": "07",
        "unit": "%",
        "convert": lambda A: A,
        "obd": obd.commands.SHORT_FUEL_TRIM_1,
        "bytes": 1,
        "dial_min": -20,
        "dial_max": 20,
        "value": 0,
        "min_read": float('inf'),
        "max_read": float('-inf'),
        "icon": "trim.png",
        "precision": 1
    },
    PID.LOAD: {
        "name": "Engine Load",
        "pid": "04",
        "unit": "%",
        "convert": lambda A: A,
        "obd": obd.commands.ENGINE_LOAD,
        "bytes": 1,
        "dial_min": 0,
        "dial_max": 100,
        "value": 0,
        "min_read": float('inf'),
        "max_read": float('-inf'),
        "icon": "load.png",
        "precision": 0
    },
}

class AssistKey(Enum):
    ECO_STATUS = "eco_status"
    SHIFT_HINT = "shift_hint"
    WARMUP_STATUS = "warmup_status"
    RESPONSIVENESS_LABEL = "responsiveness_label"
    BATTERY_STATUS = "battery_status"
    THROTTLE_STYLE = "throttle_style"


DRIVER_ASSISTS_STATE = {
    AssistKey.ECO_STATUS: {
        "name": "Eco Status",
        "value": "--",
        "show": True,
        "icon": "eco.png",
    },
    AssistKey.SHIFT_HINT: {
        "name": "Shift Hint",
        "value": "--",
        "show": True,
        "icon": "shift.png",
    },
    AssistKey.WARMUP_STATUS: {
        "name": "Engine Warmup Status",
        "value": "--",
        "show": True,
        "icon": "enginecold.png",
    },
    AssistKey.RESPONSIVENESS_LABEL: {
        "name": "Engine Responsiveness",
        "value": "--",
        "show": True,
        "icon": "responsiveness.png",
    },
    AssistKey.BATTERY_STATUS: {
        "name": "Battery Status",
        "value": "--",
        "show": True,
        "icon": "batterywarning.png",
    },
    AssistKey.THROTTLE_STYLE: {
        "name": "Drive Style",
        "value": "--",
        "show": True,
        "icon": "drivestyle.png",
    }
}

DRIVER_ASSISTS_INTERNAL_STATE = {
    "prev_throttle": None
}

GAUGES_TO_SHOW = [PID.BOOST, PID.IAT, PID.TIMING, PID.COOLANT_TEMP, PID.OIL_TEMP, PID.VOLTAGE]
DATACELLS_TO_SHOW = [PID.BOOST, PID.IAT, PID.TIMING, PID.COOLANT_TEMP, PID.OIL_TEMP, PID.VOLTAGE]
WARNINGS_TO_SHOW = [AssistKey.WARMUP_STATUS, AssistKey.BATTERY_STATUS]

FRAME_RE = re.compile(r"Frame ID:\s*([0-9A-Fa-f]+),\s*Data:\s*([0-9A-Fa-f ]+)")

def get_obd_connection():
    try:
        connection = obd.OBD(f"socket://{OBD_WIFI_IP}:{OBD_WIFI_PORT}")  
        print("[*] OBD WiFi connection:", "Connected" if connection.is_connected() else "Failed")
        return connection
    except Exception as e:
        print(f"[!] Error connecting to ELM327: {e}")
        return None

def start_driver_assist_calcs():
    print("[*] Starting Driver Assists thread...")
    while True:
        update_driver_assists()
        time.sleep(0.5)
        print()

def update_driver_assists():
    try:
        throttle = float(DATA[PID.THROTTLE]['value'])
        load = float(DATA[PID.LOAD]['value'])
        afr = float(DATA[PID.AFR]['value'])
        rpm = float(DATA[PID.RPM]['value'])
        ltft = float(DATA[PID.LTFT]['value'])
        stft = float(DATA[PID.STFT]['value'])
        coolant = float(DATA[PID.COOLANT_TEMP]['value'])
        oil = float(DATA[PID.OIL_TEMP]['value'])
        timing = float(DATA[PID.TIMING]['value'])
        iat = float(DATA[PID.IAT]['value'])
        voltage = float(DATA[PID.VOLTAGE]['value'])

        # 1. Eco DrivingTrue
        eco = []
        if load > 80 or throttle > 70 or afr < 0.95:
            eco.append("Inefficient driving")
        elif throttle < 20 and rpm > 3000:
            eco.append("Upshift recommended")
        if ltft < -5:
            eco.append("Rich fuel trim detected")
        DRIVER_ASSISTS_STATE[AssistKey.ECO_STATUS] = "Eco Status: " + (", ".join(eco) if eco else "Good")

        # 2. Shift Suggestion
        if rpm > 3500 and throttle < 30:
            DRIVER_ASSISTS_STATE[AssistKey.SHIFT_HINT] = "Shift Hint: Upshift"
        elif rpm < 1500 and load > 80:
            DRIVER_ASSISTS_STATE[AssistKey.SHIFT_HINT] = "Shift Hint: Downshift"
        else:
            DRIVER_ASSISTS_STATE[AssistKey.SHIFT_HINT] = "Shift Hint: --"

        # 3. Warmup
        if oil < 40:
            DRIVER_ASSISTS_STATE[AssistKey.WARMUP_STATUS]["value"] = "Idle"
            DRIVER_ASSISTS_STATE[AssistKey.WARMUP_STATUS]["show"] = True
        elif oil < 60 or coolant < 60:
            DRIVER_ASSISTS_STATE[AssistKey.WARMUP_STATUS]["value"]= "Drive Gently"
            DRIVER_ASSISTS_STATE[AssistKey.WARMUP_STATUS]["show"] = True
        elif oil < 80 or coolant < 80:
            DRIVER_ASSISTS_STATE[AssistKey.WARMUP_STATUS]["value"]  = "Almost Ready"
            DRIVER_ASSISTS_STATE[AssistKey.WARMUP_STATUS]["show"] = True
        else:
            DRIVER_ASSISTS_STATE[AssistKey.WARMUP_STATUS]["show"] = False

        # 4. Responsiveness
        score = 100
        if iat > 50: score -= 20
        if abs(ltft) > 5: score -= 20
        if abs(stft) > 5: score -= 10
        if timing < 10: score -= 15
        if load < 20: score -= 10
        label = "TUNED" if score > 80 else "OK" if score > 50 else "HEATSOAKED" if score > 30 else "DULL"
        DRIVER_ASSISTS_STATE[AssistKey.RESPONSIVENESS_LABEL] = f"RESPONSIVENESS: {label} ({score})"

        # 5. Battery
        if voltage < 12.6:
            DRIVER_ASSISTS_STATE[AssistKey.BATTERY_STATUS]["value"] = "Low Voltage"
            DRIVER_ASSISTS_STATE[AssistKey.BATTERY_STATUS]["show"] = True
        elif voltage > 14.7:
            DRIVER_ASSISTS_STATE[AssistKey.BATTERY_STATUS]["value"] = "Overcharging"
            DRIVER_ASSISTS_STATE[AssistKey.BATTERY_STATUS]["show"] = True
        else:
            DRIVER_ASSISTS_STATE[AssistKey.BATTERY_STATUS]["show"] = False


        # 6. Throttle Sensitivity Coach
        prev_throttle = DRIVER_ASSISTS_INTERNAL_STATE.get("prev_throttle")
        if prev_throttle is None:
            DRIVER_ASSISTS_INTERNAL_STATE["prev_throttle"] = throttle
            return

        delta_throttle = abs(throttle - prev_throttle)
        rate = delta_throttle / 0.5  # 0.5s interval

        if rate > 100:
            style = "Throttle Style: AGGRESSIVE"
        elif rate > 20:
            style = "Throttle Style: MODERATE"
        else:
            style = "Throttle Style: SMOOTH"

        DRIVER_ASSISTS_STATE[AssistKey.THROTTLE_STYLE] = style
        DRIVER_ASSISTS_INTERNAL_STATE["prev_throttle"] = throttle

    except Exception as e:
        import traceback
        traceback.print_exc()
        print("[Assist Error]", e)


def start_obd_polling():
    if USE_FAKE_OBD:
        print("[*] Running in FAKE OBD mode.")

        t = threading.Thread(target=start_driver_assist_calcs, daemon=True)
        t.start()


        rpm = 800
        throttle = 10
        boost = -1
        timing = 10

        while True:
            time.sleep(0.5)
            for pid, entry in DATA.items():
                if pid == PID.RPM:
                    rpm += random.uniform(-150, 300)
                    rpm = max(700, min(rpm, 6300))
                    go = 1
                    if rpm == 6300:
                        if go > 5:
                            rpm = 4200
                            go = 0
                        go += 1

                    value = rpm

                elif pid == PID.THROTTLE:
                    throttle += random.uniform(-4, 6)
                    throttle = max(5, min(throttle, 95))
                    value = throttle

                elif pid == PID.LOAD:
                    value = throttle * random.uniform(0.9, 1.4)
                    value = max(10, min(value, 100))

                elif pid == PID.IAT:
                    value = random.uniform(35, 65)

                elif pid == PID.COOLANT_TEMP:
                    value = random.uniform(40, 105)

                elif pid == PID.OIL_TEMP:
                    value = random.uniform(40, 105)

                elif pid == PID.STFT:
                    value = random.uniform(-6.5, 6.5)

                elif pid == PID.LTFT:
                    value = random.uniform(-4.0, 4.0)

                elif pid == PID.TIMING:
                    timing += random.uniform(-1.5, 2.5)
                    timing = max(-10, min(timing, 45))
                    value = timing

                elif pid == PID.BOOST:
                    boost += random.uniform(-0.7, 1.2)
                    boost = max(-4.5, min(boost, 10.5))
                    value = boost / 0.145 + 14.5  # Invert the convert()

                elif pid == PID.VOLTAGE:
                    value = random.uniform(13.2, 14.6)

                elif pid == PID.SPEED:
                    value = random.uniform(0, 160)

                elif pid == PID.AFR:
                    value = random.uniform(0.88, 1.1) * 32768 / 256  # Inverse of conversion

                else:
                    value = random.uniform(float(entry["dial_min"]), float(entry["dial_max"]))

                # Convert and format value
                converted = entry["convert"](value)
                precision = entry["precision"]
                truncated = f"{converted:.{precision}f}"

                # Store updated values
                entry["value"] = truncated
                entry["min_read"] = str(min(float(entry["min_read"]), float(truncated)))
                entry["max_read"] = str(max(float(entry["max_read"]), float(truncated)))

    connection = get_obd_connection()
    while not connection or not connection.is_connected():

        print("[!] Unable to connect to ELM327. Trying again...")
        connection = get_obd_connection()

    print("[*] Starting OBD polling thread...")

    t = threading.Thread(target=start_driver_assist_calcs, daemon=True)
    t.start()

    while True:
        for pid, entry in DATA.items():
            try:
                cmd = entry["obd"]
                response = connection.query(cmd)
                if not response.is_null() and response.value is not None:
                    raw_value = response.value.magnitude
                    converted_value = DATA[pid]["convert"](raw_value) if pid != "42" else raw_value  # already V
                    precision = DATA[pid]["precision"]

                    # Truncate value to desired precision (as string), no rounding
                    truncated_value = f"{converted_value:.{precision}f}"

                    # Store and update fields
                    DATA[pid]["value"] = truncated_value
                    DATA[pid]["min_read"] = str(min(float(DATA[pid]["min_read"]), float(truncated_value)))
                    DATA[pid]["max_read"] = str(max(float(DATA[pid]["max_read"]), float(truncated_value)))

            except Exception as e:
                print(f"[!] Error querying {pid}: {e}")

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


        # Add the widgets to the horizontal layout
        readings_box.add_widget(self.min_val)
        readings_box.add_widget(self.separator)
        readings_box.add_widget(self.max_val)

        self.add_widget(self.title)
        self.add_widget(self.value)
        self.add_widget(readings_box)

        with self.canvas.after:
            # Color(0.7, 0.7, 0.7, 1)  # Gray

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

    def __init__(self, label, icon_source, min_val, max_val, **kwargs):
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
        min_obj = CoreLabel(text=min_val, font_size=24, font_name=path.join(ASSETS_FONTS_PATH, "Barlow_Condensed", "BarlowCondensed-Bold.ttf"))
        min_obj.refresh()
        self.min_texture = min_obj.texture

        # Max value texture
        max_obj = CoreLabel(text=max_val, font_size=24, font_name=path.join(ASSETS_FONTS_PATH, "Barlow_Condensed", "BarlowCondensed-Bold.ttf"))
        max_obj.refresh()
        self.max_texture = max_obj.texture

        # Icon texture (if provided)
        if icon_source:
            icon_obj = CoreImage(path.join(ASSETS_ICONS_PATH, icon_source))
            self.icon_texture = icon_obj.texture
        else:
            self.icon_texture = None

        with self.canvas.before:
            # Gauge background
            self.bg = Rectangle(source=path.join(ASSETS_ICONS_PATH, "guage_bg.png"), pos=self.pos, size=self.size)

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
            self.needle = Rectangle(source=path.join(ASSETS_ICONS_PATH, "blue_needle_cleaned.png"), pos=self.pos, size=self.size)
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
        self.rot.origin = (cx, cy - 66)
        self.rot.angle = self.angle

        # Title label (centered above)
        self.label_rect.pos = (cx - self.label_texture.size[0] / 2 + 36, self.top - 110)

        # Min and max labels
        self.min_rect.pos = (self.x + 20, self.y + 76)
        self.max_rect.pos = (self.right - self.max_texture.size[0] - 20, self.y + 80)

        # Icon
        if self.icon_rect:
            self.icon_rect.pos = (cx - 32, self.top - 120)

class RPMBar(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="horizontal", **kwargs)
        self.padding = (15, 0, 0, 0)
        self.spacing = 0
        self.redline_rpm  = 6000
        self._blink_ev    = None
        self._blink_state = True

        with self.canvas.before:
            self.bg_texture = CoreImage(
                path.join(ASSETS_ICONS_PATH, "gradient_bar.png")
            ).texture
            self.bg_rect = Rectangle(texture=self.bg_texture,
                                     pos=self.pos, size=self.size)

            Color(0, 0, 0, 1)
            self.mask_rect = Rectangle(pos=self.pos, size=self.size)

            # Color(1, 1, 1, 1)
            # self.border_rect = Line(rectangle=(self.x, self.y,
            #                                    self.width, self.height),
            #                          width=1)

        self.bind(pos=self._update_geometry, size=self._update_geometry)

        self.label = Label(
            text="6300",
            font_size=56,
            halign="left",
            valign="middle",
            width=160,
            size_hint=(None, 1),
            font_name=path.join(ASSETS_FONTS_PATH,
                                "Michroma", "Michroma-Regular.ttf")
        )
        self.label.bind(
            texture_size=lambda inst, s: setattr(inst, "width", max(160, s[0]))
        )
        self.add_widget(self.label)

        Clock.schedule_interval(self._refresh, 1 / 60) 


    def _update_geometry(self, *_):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

        # self.border_rect.rectangle = (self.x, self.y, self.width, self.height)

    def _refresh(self, _dt):
        try:
            entry = DATA[PID.RPM]
            rpm_val  = float(entry["value"])
            rpm_min  = 0
            rpm_max  = 6300

            rpm_val = max(rpm_min, min(rpm_val, rpm_max))
            self.label.text = f"{round(rpm_val)}"

            frac = (rpm_val - rpm_min) / (rpm_max - rpm_min) if rpm_max != rpm_min else 0
            frac = max(0.0, min(frac, 1.0))   # 0 → 1

            mask_width = self.width * (1.0 - frac)
            self.mask_rect.size = (mask_width, self.height)
            self.mask_rect.pos = (self.x + self.width - mask_width, self.y)
            self._handle_redline_blink(rpm_val)
        except KeyError:
            self.label.text = "N/A"
            self.mask_rect.size = (self.width, self.height)

    def _handle_redline_blink(self, rpm_val):
        if rpm_val >= self.redline_rpm:
            if self._blink_ev is None:            # start blinking
                self._blink_ev = Clock.schedule_interval(
                    self._toggle_blink, 0.15)     # toggle every 150 ms
        else:
            if self._blink_ev is not None:        # stop blinking
                self._blink_ev.cancel()
                self._blink_ev = None
                self.opacity = 1            # ensure fully visible

    def _toggle_blink(self, _dt):
        self._blink_state = not self._blink_state
        self.opacity = 1 if self._blink_state else 0

class WarningBox(BoxLayout):
    def __init__(self, title, icon_source, message, assist, **kwargs):
        super().__init__(
            orientation="vertical",
            padding=(1),   # (left, top, right, bottom) in px
            **kwargs
        )
        self.assist = assist
        self.size_hint = (None, None)

        # Icon centered
        self.icon = Image(
            source=path.join(ASSETS_ICONS_PATH, icon_source),
            size_hint=(None, None),
            size=(64, 64),
            pos_hint={"center_x": 0.5},
        )
        self.add_widget(self.icon)

        # Label content centered
        self.label = Label(
            text=message,
            font_size=18,
            halign="center",
            valign="middle",
            size_hint=(1, 1),
            font_name=path.join(ASSETS_FONTS_PATH, "Barlow_Condensed", "BarlowCondensed-Regular.ttf")
        )
        self.label.bind(size=self._update_text_size)
        self.add_widget(self.label)

        Clock.schedule_interval(self._refresh, 2)

    def _update_text_size(self, instance, size):
        instance.text_size = size

    def _refresh(self, _dt):
        message = DRIVER_ASSISTS_STATE[self.assist]["value"]
        show = DRIVER_ASSISTS_STATE[self.assist]["show"]
        self.label.text = message

        self.opacity  = 1 if show else 0
        self.disabled = not show

class GaugeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        window_size = Window.size
        self.size = window_size
        root = BoxLayout(orientation="vertical", size=self.size)
        gauges_layout = GridLayout(
            cols=3, rows=2,
            spacing=0,
            size_hint=(None, None), 
            width=960, height=490, 
            pos_hint={"center_x": 0.5}
        )
        header_layout = BoxLayout(orientation="horizontal", size_hint=(1, None), height=100)

        with header_layout.canvas.before:
            Color(0, 0, 0, 1)
            self.bg_rect = Rectangle(size=header_layout.size, pos=header_layout.pos)

            def update_rect(*_):
                self.bg_rect.size = header_layout.size
                self.bg_rect.pos = header_layout.pos

            header_layout.bind(pos=update_rect, size=update_rect)

        # Warnings fixed-width layout
        warnings_layout = BoxLayout(size_hint=(None, 1), width=120 * len(WARNINGS_TO_SHOW), spacing=10, padding=5)
        for w in WARNINGS_TO_SHOW:
            entry = DRIVER_ASSISTS_STATE[w]
            warning_box = WarningBox(entry["name"], icon_source=entry["icon"], message=entry["value"], assist=w)
            warnings_layout.add_widget(warning_box)

        # RPM bar fills remaining space
        rpm_bar = RPMBar(size_hint=(1, 1))

        header_layout.add_widget(warnings_layout)
        header_layout.add_widget(rpm_bar)


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
        anim = Animation(angle=target_angle, duration=0.1, t='out_quad')
        anim.start(gauge)

class GaugeContainer(BoxLayout):
    def __init__(self, label, icon_source, min_val, max_val, **kwargs):
        super().__init__(orientation="vertical", spacing=4, padding=4, **kwargs)
        self.size_hint = (None, None)

        # Icon
        self.icon = Image(source=path.join(ASSETS_ICONS_PATH, icon_source), size_hint=(None, None), size=(32, 32))
        self.icon.opacity = 1
        self.icon.allow_stretch = True
        self.icon.keep_ratio = True
        self.icon.pos_hint = {"center_x": 0.5}
        self.add_widget(self.icon)

        # Gauge widget
        self.gauge = GaugeWidget(label, path.join(ASSETS_ICONS_PATH, icon_source), min_val, max_val)
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
        threading.Thread(target=start_obd_polling, daemon=True).start()

if __name__ == '__main__':
    DashApp().run()

