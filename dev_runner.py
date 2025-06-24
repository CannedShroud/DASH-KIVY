import os
import sys
import subprocess
import threading
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ✅ Path to your Kivy app entry file
COMMAND = ["bash", "-c", "DISPLAY=:0 uv run elm.py"]

# ✅ Debounce delay
RELOAD_DELAY = 0.8


class DebouncedHandler(FileSystemEventHandler):
    def __init__(self, command):
        self.command = command
        self.process = None
        self.lock = threading.Lock()
        self.last_change_time = 0
        self.running = True

        self.start_process()

    def start_process(self):
        print("🚀 Launching Kivy app...")
        self.process = subprocess.Popen(self.command)
        print("✅ App launched.")

    def restart_process(self):
        with self.lock:
            if self.process:
                print("🛑 Killing current process...")
                self.process.kill()
                self.process.wait()
                print("🔁 Restarting process...")
                time.sleep(0.5)  # prevent too-fast restarts

            self.process = subprocess.Popen(self.command)
            print("✅ Relaunched.")

    def on_any_event(self, event):
        if event.src_path.endswith(".py"):
            now = time.time()
            if now - self.last_change_time > RELOAD_DELAY:
                print(f"💡 Change detected: {event.src_path}")
                self.last_change_time = now
                threading.Thread(target=self.restart_process).start()

    def stop(self):
        with self.lock:
            if self.process:
                self.process.kill()
                self.process.wait()


def main():
    path = os.path.abspath(".")
    handler = DebouncedHandler(COMMAND)
    observer = Observer()
    observer.schedule(handler, path=path, recursive=True)
    observer.start()

    print("👀 Watching for changes in", path)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("👋 Stopping watcher...")
        handler.stop()
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()

