import time
import threading
from datetime import datetime, timedelta, timezone
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

from time_sync import TimeSynchronizer, KST
from clicker import FastClicker, precision_wait_and_click
from hotkey_manager import HotkeyManager
from config_manager import load_config, save_config
from time_parser import parse_target_time

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TimePickerWindow(ctk.CTkToplevel):
    """목표 시각을 시/분/초/밀리초 스핀박스로 설정할 수 있는 팝업 창"""
    def __init__(self, parent, initial_dt: datetime, on_select_callback):
        super().__init__(parent)
        self.title("⏱️ 목표 시각 사용자 설정 (Time Picker)")
        self.geometry("380x280")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.on_select_callback = on_select_callback

        ctk.CTkLabel(self, text="🎯 목표 시각을 직접 맞추세요", font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(15, 10))

        # Time Selection Container
        picker_frame = ctk.CTkFrame(self, fg_color="transparent")
        picker_frame.pack(pady=10)

        # Hours
        ctk.CTkLabel(picker_frame, text="시 (Hour)").grid(row=0, column=0, padx=5)
        self.h_var = ctk.StringVar(value=f"{initial_dt.hour:02d}")
        self.h_opt = ctk.CTkOptionMenu(picker_frame, values=[f"{i:02d}" for i in range(24)], variable=self.h_var, width=70)
        self.h_opt.grid(row=1, column=0, padx=5)

        ctk.CTkLabel(picker_frame, text=":").grid(row=1, column=1)

        # Minutes
        ctk.CTkLabel(picker_frame, text="분 (Min)").grid(row=0, column=2, padx=5)
        self.m_var = ctk.StringVar(value=f"{initial_dt.minute:02d}")
        self.m_opt = ctk.CTkOptionMenu(picker_frame, values=[f"{i:02d}" for i in range(60)], variable=self.m_var, width=70)
        self.m_opt.grid(row=1, column=2, padx=5)

        ctk.CTkLabel(picker_frame, text=":").grid(row=1, column=3)

        # Seconds
        ctk.CTkLabel(picker_frame, text="초 (Sec)").grid(row=0, column=4, padx=5)
        self.s_var = ctk.StringVar(value=f"{initial_dt.second:02d}")
        self.s_opt = ctk.CTkOptionMenu(picker_frame, values=[f"{i:02d}" for i in range(60)], variable=self.s_var, width=70)
        self.s_opt.grid(row=1, column=4, padx=5)

        ctk.CTkLabel(picker_frame, text=".").grid(row=1, column=5)

        # Milliseconds
        ctk.CTkLabel(picker_frame, text="ms").grid(row=0, column=6, padx=5)
        ms_val = int(initial_dt.microsecond / 1000)
        self.ms_entry = ctk.CTkEntry(picker_frame, width=55, placeholder_text="000")
        self.ms_entry.insert(0, f"{ms_val:03d}")
        self.ms_entry.grid(row=1, column=6, padx=5)

        # Day selection (오늘 / 내일)
        day_frame = ctk.CTkFrame(self, fg_color="transparent")
        day_frame.pack(pady=10)
        self.day_var = ctk.StringVar(value="오늘")
        ctk.CTkRadioButton(day_frame, text="오늘", variable=self.day_var, value="오늘").pack(side="left", padx=10)
        ctk.CTkRadioButton(day_frame, text="내일", variable=self.day_var, value="내일").pack(side="left", padx=10)

        # Confirm Button
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="확인 및 적용", width=120, fg_color="#10B981", hover_color="#059669", command=self.on_confirm).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="취소", width=80, fg_color="#4B5563", command=self.destroy).pack(side="left", padx=5)

    def on_confirm(self):
        try:
            h = self.h_var.get()
            m = self.m_var.get()
            s = self.s_var.get()
            ms_raw = self.ms_entry.get().strip() or "0"
            ms = int(ms_raw)
            day_prefix = "내일 " if self.day_var.get() == "내일" else ""
            res_str = f"{day_prefix}{h}:{m}:{s}.{ms:03d}"
            self.on_select_callback(res_str)
            self.destroy()
        except ValueError:
            messagebox.showerror("오류", "밀리초(ms)는 숫자이어야 합니다.")


class SugangApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("⚡ 수강신청 초정밀 타이머 & 자동 클릭 보조 프로그램 v1.1")
        self.geometry("640x840")
        self.minsize(600, 750)

        # Config & Engine
        self.config = load_config()
        self.time_sync = TimeSynchronizer()
        self.stop_event = threading.Event()
        self.reservation_thread = None

        # UI Components init
        self._setup_ui()

        # Hotkey Manager
        self.hotkey_mgr = HotkeyManager(
            on_capture_coord=self._trigger_hotkey_capture,
            on_start=self._trigger_hotkey_start,
            on_stop=self._trigger_hotkey_stop
        )
        self.hotkey_mgr.start()

        # Load Saved Config into UI
        self._load_config_to_ui()

        # Start UI Clock Update loop (10ms interval)
        self.update_clock_loop()

        # Handle Window Close
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)

        # Title Header Card
        header_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#1E1E2E")
        header_frame.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            header_frame,
            text="⚡ 수강신청 초정밀 타이머 & 클릭 매크로",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#60A5FA"
        )
        title_label.grid(row=0, column=0, padx=15, pady=(10, 2))

        # Real-time Digital Clock
        self.clock_label = ctk.CTkLabel(
            header_frame,
            text="00:00:00.000",
            font=ctk.CTkFont(family="Consolas", size=32, weight="bold"),
            text_color="#F3F4F6"
        )
        self.clock_label.grid(row=1, column=0, padx=15, pady=(0, 2))

        self.clock_status_label = ctk.CTkLabel(
            header_frame,
            text="🕒 로컬 시간 사용 중 | 단축키: [F2] 좌표캡처 | [F5] 예약시작 | [F6/ESC] 취소",
            font=ctk.CTkFont(size=11),
            text_color="#9CA3AF"
        )
        self.clock_status_label.grid(row=2, column=0, padx=15, pady=(0, 10))

        # Scrollable Container
        content_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        content_frame.grid(row=1, column=0, padx=15, pady=0, sticky="nsew")
        self.grid_rowconfigure(1, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)

        # --- Section 1: Server Time Sync ---
        sync_box = ctk.CTkFrame(content_frame, corner_radius=8)
        sync_box.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        sync_box.grid_columnconfigure(1, weight=1)

        sec1_title = ctk.CTkLabel(sync_box, text="1. 서버 시간 동기화 (네이비즘 / 수강신청 서버)", font=ctk.CTkFont(size=13, weight="bold"))
        sec1_title.grid(row=0, column=0, columnspan=3, padx=10, pady=(8, 4), sticky="w")

        ctk.CTkLabel(sync_box, text="서버 URL:").grid(row=1, column=0, padx=(10, 5), pady=5, sticky="e")
        self.url_entry = ctk.CTkEntry(sync_box, placeholder_text="예: sugang.knu.ac.kr (비워두면 로컬 시간)")
        self.url_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        self.sync_btn = ctk.CTkButton(sync_box, text="서버시간 동기화", width=120, fg_color="#2563EB", hover_color="#1D4ED8", command=self.on_sync_server_time)
        self.sync_btn.grid(row=1, column=2, padx=(5, 10), pady=5)

        self.sync_info_label = ctk.CTkLabel(sync_box, text="상태: 미동기화 (로컬 시간)", font=ctk.CTkFont(size=11), text_color="#10B981")
        self.sync_info_label.grid(row=2, column=0, columnspan=3, padx=10, pady=(0, 8), sticky="w")

        # --- Section 2: Custom Target Time & Delay ---
        target_box = ctk.CTkFrame(content_frame, corner_radius=8)
        target_box.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        target_box.grid_columnconfigure(1, weight=1)

        sec2_title = ctk.CTkLabel(target_box, text="2. 커스텀 목표 시간 & 딜레이 보정 설정", font=ctk.CTkFont(size=13, weight="bold"))
        sec2_title.grid(row=0, column=0, columnspan=4, padx=10, pady=(8, 4), sticky="w")

        ctk.CTkLabel(target_box, text="목표 시각 입력:").grid(row=1, column=0, padx=(10, 5), pady=5, sticky="e")
        
        target_input_frame = ctk.CTkFrame(target_box, fg_color="transparent")
        target_input_frame.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        target_input_frame.grid_columnconfigure(0, weight=1)

        self.target_time_entry = ctk.CTkEntry(target_input_frame, placeholder_text="10:00:00.000 또는 10시 또는 +10초", font=ctk.CTkFont(family="Consolas", size=14))
        self.target_time_entry.grid(row=0, column=0, sticky="ew")
        self.target_time_entry.bind("<KeyRelease>", self._on_target_input_change)

        self.picker_btn = ctk.CTkButton(target_input_frame, text="🎛️ 시간 선택 팝업", width=120, fg_color="#6366F1", hover_color="#4F46E5", command=self.open_time_picker)
        self.picker_btn.grid(row=0, column=1, padx=(5, 0))

        # Live Target Preview Label
        self.target_preview_label = ctk.CTkLabel(
            target_box,
            text="🎯 해석된 목표 시각: -",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#60A5FA"
        )
        self.target_preview_label.grid(row=2, column=0, columnspan=4, padx=10, pady=(0, 4), sticky="w")

        # Quick Preset & Offset Buttons Container
        presets_container = ctk.CTkFrame(target_box, fg_color="transparent")
        presets_container.grid(row=3, column=0, columnspan=4, padx=10, pady=(2, 6), sticky="ew")

        ctk.CTkLabel(presets_container, text="빠른 프리셋:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 4))
        for p_time in ["09:00:00", "10:00:00", "14:00:00", "17:00:00"]:
            ctk.CTkButton(presets_container, text=p_time[:5], width=52, height=24, fg_color="#374151", command=lambda t=p_time: self._set_target_preset(t + ".000")).pack(side="left", padx=2)

        ctk.CTkLabel(presets_container, text=" | 상대조정:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(6, 4))
        ctk.CTkButton(presets_container, text="+5초", width=45, height=24, fg_color="#1E3A8A", command=lambda: self._adjust_target_relative(seconds=5)).pack(side="left", padx=2)
        ctk.CTkButton(presets_container, text="+10초", width=45, height=24, fg_color="#1E3A8A", command=lambda: self._adjust_target_relative(seconds=10)).pack(side="left", padx=2)
        ctk.CTkButton(presets_container, text="+1분", width=45, height=24, fg_color="#1E3A8A", command=lambda: self._adjust_target_relative(minutes=1)).pack(side="left", padx=2)
        ctk.CTkButton(presets_container, text="+5분", width=45, height=24, fg_color="#1E3A8A", command=lambda: self._adjust_target_relative(minutes=5)).pack(side="left", padx=2)
        ctk.CTkButton(presets_container, text="다음 정각", width=65, height=24, fg_color="#065F46", command=self._set_next_hour_preset).pack(side="left", padx=2)

        # Delay Compensation
        ctk.CTkLabel(target_box, text="딜레이 보정 (ms):").grid(row=4, column=0, padx=(10, 5), pady=5, sticky="e")
        self.delay_entry = ctk.CTkEntry(target_box, width=100, placeholder_text="-50")
        self.delay_entry.grid(row=4, column=1, padx=5, pady=5, sticky="w")

        delay_desc = ctk.CTkLabel(target_box, text="💡 -50ms 입력 시 정각보다 50ms 일찍 클릭하여 네트워크 반응을 보정합니다.", font=ctk.CTkFont(size=11), text_color="#9CA3AF")
        delay_desc.grid(row=4, column=2, columnspan=2, padx=5, pady=5, sticky="w")

        # --- Section 3: Click Position & Multi-Click ---
        click_box = ctk.CTkFrame(content_frame, corner_radius=8)
        click_box.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        click_box.grid_columnconfigure(1, weight=1)

        sec3_title = ctk.CTkLabel(click_box, text="3. 클릭 좌표 및 클릭 옵션", font=ctk.CTkFont(size=13, weight="bold"))
        sec3_title.grid(row=0, column=0, columnspan=4, padx=10, pady=(8, 4), sticky="w")

        ctk.CTkLabel(click_box, text="목표 좌표 (X, Y):").grid(row=1, column=0, padx=(10, 5), pady=5, sticky="e")
        
        coord_inputs = ctk.CTkFrame(click_box, fg_color="transparent")
        coord_inputs.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.x_entry = ctk.CTkEntry(coord_inputs, width=70, placeholder_text="X")
        self.x_entry.pack(side="left", padx=2)
        ctk.CTkLabel(coord_inputs, text=",").pack(side="left")
        self.y_entry = ctk.CTkEntry(coord_inputs, width=70, placeholder_text="Y")
        self.y_entry.pack(side="left", padx=2)

        self.cap_btn = ctk.CTkButton(click_box, text="🎯 좌표 캡처 [F2]", width=120, fg_color="#8B5CF6", hover_color="#7C3AED", command=self.on_start_capture_coord)
        self.cap_btn.grid(row=1, column=2, padx=5, pady=5)

        self.test_click_btn = ctk.CTkButton(click_box, text="🖱️ 테스트 클릭", width=100, fg_color="#4B5563", hover_color="#374151", command=self.on_test_click)
        self.test_click_btn.grid(row=1, column=3, padx=(5, 10), pady=5)

        # Multi click options
        opts_frame = ctk.CTkFrame(click_box, fg_color="transparent")
        opts_frame.grid(row=2, column=0, columnspan=4, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(opts_frame, text="연속 클릭 횟수:").pack(side="left", padx=(0, 5))
        self.click_count_entry = ctk.CTkEntry(opts_frame, width=50)
        self.click_count_entry.pack(side="left", padx=2)
        ctk.CTkLabel(opts_frame, text="회 |").pack(side="left", padx=5)

        ctk.CTkLabel(opts_frame, text="연타 간격:").pack(side="left", padx=5)
        self.click_interval_entry = ctk.CTkEntry(opts_frame, width=50)
        self.click_interval_entry.pack(side="left", padx=2)
        ctk.CTkLabel(opts_frame, text="ms |").pack(side="left", padx=5)

        self.sound_var = ctk.BooleanVar(value=True)
        self.sound_check = ctk.CTkCheckBox(opts_frame, text="클릭 비프음", variable=self.sound_var)
        self.sound_check.pack(side="left", padx=10)

        # --- Section 4: Reservation & Countdown Bar ---
        res_box = ctk.CTkFrame(content_frame, corner_radius=8, fg_color="#1E293B")
        res_box.grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        res_box.grid_columnconfigure(0, weight=1)

        self.countdown_label = ctk.CTkLabel(
            res_box,
            text="⏳ 예약 대기 중...",
            font=ctk.CTkFont(family="Consolas", size=20, weight="bold"),
            text_color="#F59E0B"
        )
        self.countdown_label.grid(row=0, column=0, padx=10, pady=(12, 4))

        btn_container = ctk.CTkFrame(res_box, fg_color="transparent")
        btn_container.grid(row=1, column=0, padx=10, pady=(4, 12))

        self.start_btn = ctk.CTkButton(
            btn_container,
            text="🚀 예약 시작 (F5)",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=42,
            width=200,
            fg_color="#10B981",
            hover_color="#059669",
            command=self.on_start_reservation
        )
        self.start_btn.pack(side="left", padx=8)

        self.stop_btn = ctk.CTkButton(
            btn_container,
            text="🛑 예약 취소 (F6/ESC)",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=42,
            width=200,
            fg_color="#EF4444",
            hover_color="#DC2626",
            state="disabled",
            command=self.on_stop_reservation
        )
        self.stop_btn.pack(side="left", padx=8)

        # --- Section 5: Real-time Log Console ---
        log_box = ctk.CTkFrame(content_frame, corner_radius=8)
        log_box.grid(row=4, column=0, padx=5, pady=5, sticky="ew")
        log_box.grid_columnconfigure(0, weight=1)

        log_head = ctk.CTkFrame(log_box, fg_color="transparent")
        log_head.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="ew")
        log_head.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(log_head, text="📋 실행 로그", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(log_head, text="로그 비우기", width=70, height=22, fg_color="#374151", command=self.clear_log).grid(row=0, column=1, sticky="e")

        self.log_textbox = ctk.CTkTextbox(log_box, height=120, font=ctk.CTkFont(family="Consolas", size=11))
        self.log_textbox.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="ew")
        self.log_textbox.configure(state="disabled")

        # Bottom Bar
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.grid(row=2, column=0, padx=15, pady=(5, 10), sticky="ew")
        bottom_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(bottom_frame, text="💾 설정 저장", width=110, fg_color="#4F46E5", hover_color="#4338CA", command=self.on_save_config).pack(side="right")

    def log(self, text: str):
        now_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        msg = f"[{now_str}] {text}\n"
        
        def _update():
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", msg)
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")

        self.after(0, _update)

    def clear_log(self):
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

    def _load_config_to_ui(self):
        t_val = self.config.get("target_time", "10:00:00.000")
        self.target_time_entry.insert(0, t_val)
        self.url_entry.insert(0, self.config.get("target_url", ""))
        self.x_entry.insert(0, str(self.config.get("coord_x", 500)))
        self.y_entry.insert(0, str(self.config.get("coord_y", 500)))
        self.delay_entry.insert(0, str(self.config.get("delay_offset_ms", -50)))
        self.click_count_entry.insert(0, str(self.config.get("click_count", 3)))
        self.click_interval_entry.insert(0, str(self.config.get("click_interval_ms", 50)))
        self.sound_var.set(self.config.get("sound_enabled", True))
        
        # Trigger live preview update
        self._update_target_preview()
        self.log("프로그램이 시작되었습니다. 설정이 로드되었습니다.")

    def _on_target_input_change(self, event=None):
        self._update_target_preview()

    def _update_target_preview(self):
        raw_text = self.target_time_entry.get().strip()
        if not raw_text:
            self.target_preview_label.configure(text="🎯 해석된 목표 시각: -", text_color="#9CA3AF")
            return

        try:
            curr_dt = self.time_sync.get_current_datetime()
            target_dt = parse_target_time(raw_text, curr_dt)
            diff = target_dt - curr_dt
            diff_sec = diff.total_seconds()
            
            day_str = "오늘" if target_dt.date() == curr_dt.date() else "내일"
            formatted = target_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            
            if diff_sec > 0:
                self.target_preview_label.configure(
                    text=f"🎯 목표 시각: {day_str} {formatted} ({diff_sec:.1f}초 후)",
                    text_color="#60A5FA"
                )
            else:
                self.target_preview_label.configure(
                    text=f"🎯 목표 시각: {day_str} {formatted} (이미 지남 - 클릭 시 내일 적용)",
                    text_color="#F59E0B"
                )
        except Exception as e:
            self.target_preview_label.configure(
                text=f"⚠️ 목표 시각 해석 오류: {str(e)}",
                text_color="#EF4444"
            )

    def open_time_picker(self):
        try:
            curr_dt = self.time_sync.get_current_datetime()
            raw_text = self.target_time_entry.get().strip()
            init_dt = parse_target_time(raw_text, curr_dt) if raw_text else curr_dt
        except Exception:
            init_dt = self.time_sync.get_current_datetime()

        TimePickerWindow(self, init_dt, self._on_picker_select)

    def _on_picker_select(self, new_time_str: str):
        self.target_time_entry.delete(0, "end")
        self.target_time_entry.insert(0, new_time_str)
        self._update_target_preview()
        self.log(f"⏱️ 팝업을 통해 목표 시각이 '{new_time_str}' (으)로 변경되었습니다.")

    def _set_target_preset(self, time_str: str):
        self.target_time_entry.delete(0, "end")
        self.target_time_entry.insert(0, time_str)
        self._update_target_preview()
        self.log(f"목표 시각이 프리셋 '{time_str}' (으)로 설정되었습니다.")

    def _adjust_target_relative(self, seconds=0, minutes=0):
        try:
            curr_dt = self.time_sync.get_current_datetime()
            raw_text = self.target_time_entry.get().strip()
            base_target = parse_target_time(raw_text, curr_dt) if raw_text else curr_dt
        except Exception:
            base_target = self.time_sync.get_current_datetime()

        new_target = base_target + timedelta(seconds=seconds, minutes=minutes)
        t_str = new_target.strftime("%H:%M:%S.%f")[:-3]
        self._set_target_preset(t_str)

    def _set_next_hour_preset(self):
        curr_dt = self.time_sync.get_current_datetime()
        next_hour_dt = (curr_dt + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        t_str = next_hour_dt.strftime("%H:%M:%S.000")
        self._set_target_preset(t_str)

    def on_save_config(self):
        try:
            self.config["target_time"] = self.target_time_entry.get().strip()
            self.config["target_url"] = self.url_entry.get().strip()
            self.config["coord_x"] = int(self.x_entry.get().strip())
            self.config["coord_y"] = int(self.y_entry.get().strip())
            self.config["delay_offset_ms"] = float(self.delay_entry.get().strip())
            self.config["click_count"] = int(self.click_count_entry.get().strip())
            self.config["click_interval_ms"] = int(self.click_interval_entry.get().strip())
            self.config["sound_enabled"] = self.sound_var.get()
            save_config(self.config)
            self.log("💾 설정이 정상적으로 저장되었습니다.")
            messagebox.showinfo("성공", "설정이 저장되었습니다!")
        except ValueError:
            messagebox.showerror("오류", "입력값을 확인해주세요. 숫자 형식이어야 합니다.")

    def update_clock_loop(self):
        curr_dt = self.time_sync.get_current_datetime()
        time_str = curr_dt.strftime("%H:%M:%S.%f")[:-3]
        self.clock_label.configure(text=time_str)

        if self.reservation_thread and self.reservation_thread.is_alive():
            if hasattr(self, 'target_epoch'):
                curr_epoch = self.time_sync.get_current_epoch()
                rem = self.target_epoch - curr_epoch
                if rem > 0:
                    rem_sec = int(rem)
                    rem_ms = int((rem - rem_sec) * 1000)
                    hrs = rem_sec // 3600
                    mins = (rem_sec % 3600) // 60
                    secs = rem_sec % 60
                    self.countdown_label.configure(
                        text=f"⏳ 남은 시간: {hrs:02d}:{mins:02d}:{secs:02d}.{rem_ms:03d}",
                        text_color="#F59E0B"
                    )
                else:
                    self.countdown_label.configure(text="⚡ 클릭 실행 완료!", text_color="#10B981")

        self.after(15, self.update_clock_loop)

    def on_sync_server_time(self):
        url = self.url_entry.get().strip()
        self.sync_info_label.configure(text="서버 시간 요청 중...", text_color="#F59E0B")
        
        def _sync_worker():
            success, msg = self.time_sync.sync_server_time(url)
            def _update_ui():
                if success:
                    self.sync_info_label.configure(text=self.time_sync.sync_status, text_color="#10B981")
                    self.clock_status_label.configure(text=f"🌐 서버 시간 동기화됨 ({url}) | Ping: {self.time_sync.rtt_ms:.1f}ms")
                    self.log(f"서버 시간 동기화 성공: {msg}")
                else:
                    self.sync_info_label.configure(text=msg, text_color="#EF4444")
                    self.clock_status_label.configure(text="🕒 로컬 시간 사용 중")
                    self.log(f"서버 시간 동기화 경고: {msg}")
                self._update_target_preview()
            self.after(0, _update_ui)

        threading.Thread(target=_sync_worker, daemon=True).start()

    def _trigger_hotkey_capture(self):
        self.after(0, self.on_start_capture_coord)

    def _trigger_hotkey_start(self):
        self.after(0, self.on_start_reservation)

    def _trigger_hotkey_stop(self):
        self.after(0, self.on_stop_reservation)

    def on_start_capture_coord(self):
        self.log("🎯 2초 후 마우스 위치를 캡처합니다! 마우스를 원하는 버튼에 올려놓으세요...")
        self.cap_btn.configure(state="disabled", text="캡처 중... (2초)")

        def _do_cap():
            time.sleep(2.0)
            pos_x, pos_y = FastClicker.get_current_cursor_pos()
            def _update():
                self.x_entry.delete(0, "end")
                self.x_entry.insert(0, str(pos_x))
                self.y_entry.delete(0, "end")
                self.y_entry.insert(0, str(pos_y))
                self.cap_btn.configure(state="normal", text="🎯 좌표 캡처 [F2]")
                self.log(f"🎯 좌표 캡처 완료: X={pos_x}, Y={pos_y}")
            self.after(0, _update)

        threading.Thread(target=_do_cap, daemon=True).start()

    def on_test_click(self):
        try:
            x = int(self.x_entry.get().strip())
            y = int(self.y_entry.get().strip())
            count = int(self.click_count_entry.get().strip())
            interval = int(self.click_interval_entry.get().strip())
            sound = self.sound_var.get()
            self.log(f"🖱️ 테스트 클릭 실행: ({x}, {y}), {count}회")
            FastClicker.execute_click(x, y, count=count, interval_ms=interval, sound=sound)
        except ValueError:
            messagebox.showerror("오류", "좌표 및 클릭 횟수는 정수이어야 합니다.")

    def on_start_reservation(self):
        if self.reservation_thread and self.reservation_thread.is_alive():
            messagebox.showwarning("경고", "이미 예약이 진행 중입니다.")
            return

        try:
            target_str = self.target_time_entry.get().strip()
            x = int(self.x_entry.get().strip())
            y = int(self.y_entry.get().strip())
            delay_ms = float(self.delay_entry.get().strip())
            count = int(self.click_count_entry.get().strip())
            interval_ms = int(self.click_interval_entry.get().strip())
            sound = self.sound_var.get()

            # Parse Target Time using versatile parser
            curr_dt = self.time_sync.get_current_datetime()
            target_dt = parse_target_time(target_str, curr_dt)

            # Apply delay compensation (delay_ms)
            actual_target_dt = target_dt + timedelta(milliseconds=delay_ms)
            self.target_epoch = actual_target_dt.timestamp()

            self.stop_event.clear()

            # UI Update
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.countdown_label.configure(text="⏳ 타이머 가동 중...", text_color="#F59E0B")
            
            target_formatted = target_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            actual_formatted = actual_target_dt.strftime("%H:%M:%S.%f")[:-3]
            self.log(f"🚀 예약 설정 완료! 목표 시각: {target_formatted} (보정: {delay_ms:+.1f}ms) -> 실제 클릭 시각: {actual_formatted}")

            # Run in worker thread
            def _worker():
                success = precision_wait_and_click(
                    target_epoch=self.target_epoch,
                    x=x,
                    y=y,
                    count=count,
                    interval_ms=interval_ms,
                    sound=sound,
                    time_offset=self.time_sync.time_offset,
                    stop_event=self.stop_event,
                    log_callback=self.log
                )
                def _reset_ui():
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    if success:
                        self.countdown_label.configure(text="✅ 클릭 완료!", text_color="#10B981")
                    else:
                        self.countdown_label.configure(text="🛑 예약 취소됨", text_color="#EF4444")
                self.after(0, _reset_ui)

            self.reservation_thread = threading.Thread(target=_worker, daemon=True)
            self.reservation_thread.start()

        except Exception as e:
            messagebox.showerror("입력 오류", f"목표 시각 또는 설정값을 확인해주세요:\n{str(e)}")

    def on_stop_reservation(self):
        if self.reservation_thread and self.reservation_thread.is_alive():
            self.stop_event.set()
            self.log("🛑 사용자에 의해 클릭 예약이 취소되었습니다.")
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.countdown_label.configure(text="🛑 예약 취소됨", text_color="#EF4444")

    def on_close(self):
        self.stop_event.set()
        if hasattr(self, 'hotkey_mgr'):
            self.hotkey_mgr.stop()
        self.destroy()
