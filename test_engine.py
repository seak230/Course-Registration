from datetime import datetime, timezone, timedelta
from time_parser import parse_target_time, KST

def test():
    base_dt = datetime(2026, 8, 12, 10, 0, 0, tzinfo=KST)
    test_inputs = [
        "10:00:00.500",
        "100000",
        "093000",
        "14시 30분 0초",
        "오후 2시 15분",
        "+10초",
        "+5분",
        "내일 10:00:00"
    ]

    print("--- Testing Time Parser ---")
    for inp in test_inputs:
        res = parse_target_time(inp, base_dt)
        print(f"Input: '{inp}' -> Parsed: {res.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")

if __name__ == "__main__":
    test()
