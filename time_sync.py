import time
import requests
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

KST = timezone(timedelta(hours=9))

class TimeSynchronizer:
    def __init__(self):
        self.use_server_time = False
        self.target_url = ""
        self.time_offset = 0.0  # seconds: server_time - local_time
        self.rtt_ms = 0.0        # Round trip time in milliseconds
        self.last_sync_time = None
        self.sync_status = "로컬 시간 사용 중"

    def sync_server_time(self, url: str) -> tuple[bool, str]:
        """
        Target URL의 HTTP 헤더 'Date'를 읽어서 서버 시간과 로컬 시간의 오차(Offset)를 구합니다.
        """
        if not url:
            self.use_server_time = False
            self.time_offset = 0.0
            self.rtt_ms = 0.0
            self.sync_status = "로컬 시간 사용 중"
            return False, "URL이 입력되지 않아 로컬 시간을 사용합니다."

        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        self.target_url = url

        try:
            # RTT 측정을 포함한 HEAD 요청
            start_perf = time.perf_counter()
            start_local = time.time()
            
            # User-Agent 설정
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            # HEAD 요청 시도 (안되는 경우 GET으로  fallback)
            try:
                response = requests.head(url, headers=headers, timeout=3.0, allow_redirects=True)
            except Exception:
                response = requests.get(url, headers=headers, timeout=3.0, allow_redirects=True)

            end_perf = time.perf_counter()
            end_local = time.time()

            rtt = (end_perf - start_perf) * 1000.0  # ms
            self.rtt_ms = rtt

            date_str = response.headers.get("Date")
            if not date_str:
                self.use_server_time = False
                self.time_offset = 0.0
                self.sync_status = "서버 Date 헤더 없음 (로컬 시간 사용)"
                return False, "서버의 Date 헤더를 찾을 수 없습니다."

            # Date 헤더 파싱 (GMT)
            server_dt = parsedate_to_datetime(date_str)
            # KST로 변환
            server_dt_kst = server_dt.astimezone(KST)
            server_epoch = server_dt_kst.timestamp()

            # HTTP Date는 초 단위 정수이므로, RTT/2를 반영한 추정 서버 시간
            estimated_server_epoch = server_epoch + (rtt / 2000.0)
            
            # 로컬 시간 측정 중간 지점
            mid_local_epoch = (start_local + end_local) / 2.0
            
            # offset = (추정 서버 시간) - (로컬 시간)
            self.time_offset = estimated_server_epoch - mid_local_epoch
            self.use_server_time = True
            self.last_sync_time = datetime.now(KST)
            
            sign = "+" if self.time_offset >= 0 else ""
            self.sync_status = f"동기화 완료 (오차: {sign}{self.time_offset*1000:.1f}ms, Ping: {rtt:.1f}ms)"
            return True, self.sync_status

        except Exception as e:
            self.use_server_time = False
            self.time_offset = 0.0
            self.sync_status = f"동기화 실패: {str(e)}"
            return False, f"서버 시간 요청 실패: {str(e)}"

    def get_current_epoch(self) -> float:
        return time.time() + self.time_offset

    def get_current_datetime(self) -> datetime:
        curr_epoch = time.time() + self.time_offset
        return datetime.fromtimestamp(curr_epoch, tz=KST)
