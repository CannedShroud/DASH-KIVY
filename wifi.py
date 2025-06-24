from kivy.config import Config
Config.set("graphics", "fullscreen", "auto")
Config.set('graphics', 'show_cursor', '0')

from kivy.core.window import Window
Window.show_cursor = False

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
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
import threading
import re
from math import inf
import random
import obd
from enum import Enum
from os import path

USE_FAKE_OBD = True
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

GAUGES_TO_SHOW = [PID.BOOST, PID.IAT, PID.TIMING, PID.COOLANT_TEMP, PID.OIL_TEMP, PID.VOLTAGE]
DATACELLS_TO_SHOW = [PID.BOOST, PID.IAT, PID.TIMING, PID.COOLANT_TEMP, PID.OIL_TEMP, PID.VOLTAGE]

FRAME_RE = re.compile(r"Frame ID:\s*([0-9A-Fa-f]+),\s*Data:\s*([0-9A-Fa-f ]+)")

def get_obd_connection():
    try:
        connection = obd.OBD(f"socket://{OBD_WIFI_IP}:{OBD_WIFI_PORT}")  
        print("[*] OBD WiFi connection:", "Connected" if connection.is_connected() else "Failed")
        return connection
    except Exception as e:
        print(f"[!] Error connecting to ELM327: {e}")
        return None

def start_obd_polling():
    if USE_FAKE_OBD:
        print("[*] Running in FAKE OBD mode.")

        rpm = 800
        throttle = 10
        boost = -1
        timing = 10

        while True:
            for pid, entry in DATA.items():
                if pid == PID.RPM:
                    rpm += random.uniform(-150, 300)
                    rpm = max(700, min(rpm, 5500))
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
                    value = random.uniform(78, 105)

                elif pid == PID.OIL_TEMP:
                    value = random.uniform(80, 115)

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

                    print(f"{DATA[pid]['name']} ({pid}): {truncated_value}")
            except Exception as e:
                print(f"[!] Error querying {pid}: {e}")

class AssistOverlay(BoxLayout):
    eco_status = StringProperty("Eco Status: --")
    shift_hint = StringProperty("Shift Hint: --")
    warmup_status = StringProperty("Engine: --")
    responsiveness_score = NumericProperty(0)
    responsiveness_label = StringProperty("RESPONSIVENESS: --")
    battery_status = StringProperty("Battery: --")
    throttle_style = StringProperty("Throttle Style: --")

    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=10, spacing=8, size_hint=(1, 0.3), **kwargs)
        self.labels = []
        for prop in ['eco_status', 'shift_hint', 'warmup_status',
                     'responsiveness_label', 'battery_status', 'throttle_style']:
            lbl = Label(text=getattr(self, prop), font_size='20sp', halign='left')
            self.labels.append(lbl)
            self.add_widget(lbl)

        Clock.schedule_interval(self.update_assists, 0.5)

    def update_assists(self, dt):

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

            # 1. Eco Driving Assistant
            eco = []
            if load > 80 or throttle > 70 or afr < 0.95:
                eco.append("Inefficient driving")
            elif throttle < 20 and rpm > 3000:
                eco.append("Upshift recommended")
            if ltft < -5:
                eco.append("Rich fuel trim detected")
            self.eco_status = "Eco Status: " + (", ".join(eco) if eco else "Good")

            # 2. Shift Suggestion
            if rpm > 3500 and throttle < 30:
                self.shift_hint = "Shift Hint: Upshift"
            elif rpm < 1500 and load > 80:
                self.shift_hint = "Shift Hint: Downshift"
            else:
                self.shift_hint = "Shift Hint: --"

            # 3. Engine Warm-Up
            if coolant < 70 or oil < 60:
                self.warmup_status = "Engine: Cold"
            elif coolant >= 85 and oil >= 85:
                self.warmup_status = "Engine: Ready"
            else:
                self.warmup_status = "Engine: Warming"

            # 4. Responsiveness Index
            score = 100
            if iat > 50: score -= 20
            if abs(ltft) > 5: score -= 20
            if abs(stft) > 5: score -= 10
            if timing < 10: score -= 15
            if load < 20: score -= 10
            self.responsiveness_score = max(0, min(100, score))
            if score > 80:
                label = "TUNED"
            elif score > 50:
                label = "OK"
            elif score > 30:
                label = "HEATSOAKED"
            else:
                label = "DULL"
            self.responsiveness_label = f"RESPONSIVENESS: {label} ({score})"

            # 5. Battery Health
            if voltage < 12.6:
                self.battery_status = "Battery: Low Voltage"
            elif voltage > 14.7:
                self.battery_status = "Battery: Overcharging"
            else:
                self.battery_status = "Battery: OK"

            # 6. Throttle Sensitivity Coach
            if not hasattr(self, '_prev_throttle'):
                self._prev_throttle = throttle
                self._prev_time = dt
                return
            delta_throttle = abs(throttle - self._prev_throttle)
            rate = delta_throttle / (dt if dt > 0 else 0.01)
            if rate > 100:
                self.throttle_style = "Throttle Style: AGGRESSIVE"
            elif rate > 20:
                self.throttle_style = "Throttle Style: MODERATE"
            else:
                self.throttle_style = "Throttle Style: SMOOTH"
            self._prev_throttle = throttle

            for prop, lbl in zip(['eco_status', 'shift_hint', 'warmup_status',
                                  'responsiveness_label', 'battery_status', 'throttle_style'], self.labels):
                lbl.text = getattr(self, prop)

        except Exception as e:
            import traceback
            traceback.print_exc()
            print("[Assist Error]", e)

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

class GaugeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = GridLayout(cols=3, rows=2, padding=25, spacing=0)

        self.gauges = []
        self.pid_to_gauge = {}

        for pid in GAUGES_TO_SHOW:
            entry = DATA[pid]
            gauge = GaugeWidget(entry["unit"], entry["icon"], str(entry["dial_min"]), str(entry["dial_max"]))
            self.pid_to_gauge[pid] = gauge
            self.gauges.append(gauge)
            layout.add_widget(gauge)

        self.add_widget(layout)
        assist = AssistOverlay()
        self.add_widget(assist)
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
        self.size = (320, 240)

        # Icon
        print(path.join(ASSETS_ICONS_PATH, icon_source))
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

