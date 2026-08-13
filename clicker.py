import time
import ctypes
import pyautogui
import platform
import winsound
import threading

# Windows API Constants for fast mouse clicking
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

class FastClicker:
    @staticmethod
    def get_current_cursor_pos() -> tuple[int, int]:
        """현재 마우스 커서의 (X, Y) 좌표 반환"""
        return pyautogui.position()

    @staticmethod
    def raw_win_click(x: int, y: int):
        """Windows user32 API를 사용한 ultra-fast 클릭"""
        if platform.system() == "Windows":
            # Set cursor position
            ctypes.windll.user32.SetCursorPos(int(x), int(y))
            # Send mouse left down and left up
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        else:
            pyautogui.click(x=x, y=y)

    @classmethod
    def execute_click(cls, x: int, y: int, count: int = 1, interval_ms: int = 50, sound: bool = True):
        """
        지정된 좌표(x, y)에 count 회 만큼 interval_ms 간격으로 클릭 수행
        """
        for i in range(count):
            cls.raw_win_click(x, y)
            if sound and i == 0:
                # 첫 클릭 시 비프음 (비동기로 실행하여 클릭 지연 방지)
                threading.Thread(target=lambda: winsound.Beep(1200, 150), daemon=True).start()
            if count > 1 and i < count - 1:
                time.sleep(interval_ms / 1000.0)


def precision_wait_and_click(
    target_epoch: float,
    x: int,
    y: int,
    count: int = 1,
    interval_ms: int = 50,
    sound: bool = True,
    time_offset: float = 0.0,
    stop_event: threading.Event = None,
    log_callback = None
):
    """
    고정밀 perf_counter 루프를 사용하여 target_epoch 시각에 정확하게 클릭을 실행합니다.
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        print(f"[PrecisionClicker] {msg}")

    log(f"예약 시작! 목표 시각 (Epoch): {target_epoch:.3f}, 좌표: ({x}, {y})")

    # 고정밀 대기 루프
    # 남은 시간이 10ms 초과이면 time.sleep(0.001)로 CPU 사용량을 줄이고,
    # 10ms 이하로 남아있으면 busy-wait(pass 루프)로 마이크로초 단위 정밀도 유지
    while True:
        if stop_event and stop_event.is_set():
            log("사용자에 의해 예약이 취소되었습니다.")
            return False

        current_time = time.time() + time_offset
        rem = target_epoch - current_time

        if rem <= 0:
            # 즉시 클릭!
            click_start_time = time.time() + time_offset
            FastClicker.execute_click(x, y, count=count, interval_ms=interval_ms, sound=sound)
            diff_ms = (click_start_time - target_epoch) * 1000.0
            log(f"⚡ [클릭 성공!] 목표 시각과의 차이: {diff_ms:+.2f}ms (좌표: {x}, {y}, 횟수: {count}회)")
            return True

        if rem > 0.015:
            # 15ms 이상 남았으면 1ms 잠자기
            time.sleep(0.002)
        elif rem > 0.002:
            # 2ms 이상 남았으면 짧게 잠자기
            time.sleep(0.0005)
        else:
            # 2ms 이하 remaining: Spin-wait (busy loop)
            pass
