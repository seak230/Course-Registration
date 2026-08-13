import json
import os

DEFAULT_CONFIG = {
    "target_time": "10:00:00.000",
    "target_url": "",
    "use_server_time": False,
    "coord_x": 500,
    "coord_y": 500,
    "delay_offset_ms": -50,  # Negative means click 50ms BEFORE target time
    "click_count": 3,        # Number of clicks
    "click_interval_ms": 50, # Interval between clicks in burst mode
    "sound_enabled": True,
    "custom_presets": ["09:00:00.000", "10:00:00.000", "14:00:00.000", "17:00:00.000"]
}

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(data)
                return config
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving config: {e}")
