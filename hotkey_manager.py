from pynput import keyboard
import threading

class HotkeyManager:
    def __init__(self, on_capture_coord=None, on_start=None, on_stop=None):
        self.on_capture_coord = on_capture_coord
        self.on_start = on_start
        self.on_stop = on_stop
        self.listener = None

    def start(self):
        """글로벌 단축키 리스너 시작"""
        if self.listener is not None:
            return

        def on_press(key):
            try:
                if key == keyboard.Key.f2:
                    if self.on_capture_coord:
                        self.on_capture_coord()
                elif key == keyboard.Key.f5:
                    if self.on_start:
                        self.on_start()
                elif key == keyboard.Key.f6 or key == keyboard.Key.esc:
                    if self.on_stop:
                        self.on_stop()
            except Exception as e:
                print(f"[HotkeyManager] Error processing hotkey: {e}")

        self.listener = keyboard.Listener(on_press=on_press)
        self.listener.daemon = True
        self.listener.start()

    def stop(self):
        """리스너 중지"""
        if self.listener is not None:
            self.listener.stop()
            self.listener = None
