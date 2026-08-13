import re
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

def parse_target_time(target_str: str, base_dt: datetime) -> datetime:
    """
    다양한 형태의 목표 시각 문자열을 해석하여 KST datetime 객체로 반환합니다.
    
    지원 포맷 예시:
    - 표준: "10:00:00.500", "10:00:00", "10:00", "09:30"
    - 연속 숫자: "100000" (10시0분0초), "093000", "1400" (14시0분)
    - 한글: "10시", "10시 0분", "오전 10시", "오후 2시 30분 0초", "10시 0분 0초 500밀리초"
    - 상대 시간: "+10초", "+1분", "+5분", "+1시간"
    - 날짜 포함: "2026-08-13 10:00:00.000", "내일 10:00:00"
    """
    if not target_str or not target_str.strip():
        raise ValueError("목표 시각을 입력해 주세요.")

    s = target_str.strip().lower()

    # 1. 상대 시간 처리 (+10초, +1분 등)
    if s.startswith("+"):
        rel_s = s[1:].strip()
        num_match = re.search(r"(\d+(\.\d+)?)", rel_s)
        if not num_match:
            raise ValueError(f"상대 시간 숫자를 인식할 수 없습니다: {target_str}")
        val = float(num_match.group(1))

        if "시간" in rel_s or "h" in rel_s:
            return base_dt + timedelta(hours=val)
        elif "분" in rel_s or "m" in rel_s:
            return base_dt + timedelta(minutes=val)
        elif "초" in rel_s or "s" in rel_s:
            return base_dt + timedelta(seconds=val)
        elif "ms" in rel_s or "밀리" in rel_s:
            return base_dt + timedelta(milliseconds=val)
        else:
            # 기본 단위는 초
            return base_dt + timedelta(seconds=val)

    # 내일/오늘 키워드 분리
    is_tomorrow = False
    if s.startswith("내일"):
        is_tomorrow = True
        s = s[2:].strip()
    elif s.startswith("오늘"):
        s = s[2:].strip()

    # 특정 날짜 지정 여부 (YYYY-MM-DD HH:MM:SS)
    date_part = None
    date_match = re.match(r"^(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})\s+(.+)$", s)
    if date_match:
        d_str = date_match.group(1).replace("/", "-").replace(".", "-")
        s = date_match.group(2).strip()
        d_parts = [int(x) for x in d_str.split("-")]
        date_part = (d_parts[0], d_parts[1], d_parts[2])

    hour, minute, second, microsec = 0, 0, 0, 0
    parsed = False

    # 2. 한글 서식 (예: 오전 10시 30분 15초 500밀리초, 오후 2시)
    if "시" in s:
        is_pm = "오후" in s or "pm" in s
        is_am = "오전" in s or "am" in s
        s_clean = re.sub(r"(오전|오후|am|pm)", "", s).strip()
        
        h_match = re.search(r"(\d+)\s*시", s_clean)
        m_match = re.search(r"(\d+)\s*분", s_clean)
        s_match = re.search(r"(\d+)\s*초", s_clean)
        ms_match = re.search(r"(\d+)\s*(ms|밀리)", s_clean)

        if h_match:
            hour = int(h_match.group(1))
            if is_pm and hour < 12:
                hour += 12
            elif is_am and hour == 12:
                hour = 0
            minute = int(m_match.group(1)) if m_match else 0
            second = int(s_match.group(1)) if s_match else 0
            microsec = int(ms_match.group(1)) * 1000 if ms_match else 0
            parsed = True

    # 3. 콜론 기반 서식 (HH:MM:SS.mmm 또는 HH:MM:SS 또는 HH:MM)
    if not parsed and ":" in s:
        parts = s.split(":")
        if len(parts) == 2:
            hour = int(parts[0])
            minute = int(parts[1])
            second = 0
            microsec = 0
            parsed = True
        elif len(parts) == 3:
            hour = int(parts[0])
            minute = int(parts[1])
            sec_part = parts[2]
            if "." in sec_part:
                sec_sub = sec_part.split(".")
                second = int(sec_sub[0])
                ms_str = sec_sub[1].ljust(6, '0')[:6]
                microsec = int(ms_str)
            else:
                second = int(sec_part)
                microsec = 0
            parsed = True

    # 4. 연속 숫자 서식 (HHMMSS -> 예: 100000, 093000, 1400)
    if not parsed and s.isdigit():
        if len(s) == 6:
            hour = int(s[0:2])
            minute = int(s[2:4])
            second = int(s[4:6])
            parsed = True
        elif len(s) == 4:
            hour = int(s[0:2])
            minute = int(s[2:4])
            second = 0
            parsed = True
        elif len(s) <= 2:
            hour = int(s)
            minute = 0
            second = 0
            parsed = True

    if not parsed:
        raise ValueError(f"시간 형식을 해석할 수 없습니다: '{target_str}'\n(올바른 예: 10:00:00.000, 100000, 10시 0분, +10초)")

    if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
        raise ValueError(f"시간 범위를 벗어났습니다: {hour}:{minute}:{second}")

    if date_part:
        res_dt = base_dt.replace(
            year=date_part[0], month=date_part[1], day=date_part[2],
            hour=hour, minute=minute, second=second, microsecond=microsec
        )
    else:
        res_dt = base_dt.replace(
            hour=hour, minute=minute, second=second, microsecond=microsec
        )
        if is_tomorrow or (res_dt < base_dt and not target_str.strip().startswith("+")):
            # 지정 시각이 이미 오늘 지난 경우 내일로 설정
            res_dt += timedelta(days=1)

    return res_dt
