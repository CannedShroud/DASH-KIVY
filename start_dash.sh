#!/bin/bash
cd /home/pi/workdir/DASH-KIVY
source .venv/bin/activate  
export DISPLAY=:0
export XDG_RUNTIME_DIR=/run/user/1000  
/home/pi/.local/bin/uv run wifi.py

