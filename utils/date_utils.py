from datetime import datetime, timedelta
import calendar

def get_weekday_korean_to_eng():
    return {
        '월': 0, '월요일': 0,
        '화': 1, '화요일': 1,
        '수': 2, '수요일': 2,
        '목': 3, '목요일': 3,
        '금': 4, '금요일': 4,
        '토': 5, '토요일': 5,
        '일': 6, '일요일': 6
    }

def parse_weekdays(text):
    """텍스트에서 요일 정보를 추출"""
    weekday_map = get_weekday_korean_to_eng()
    weekdays = []
    
    for day, num in weekday_map.items():
        if day in text:
            weekdays.append(num)
    
    return sorted(list(set(weekdays)))

def generate_recurring_dates(weekdays, start_date=None, period_days=30):
    """주어진 요일에 해당하는 날짜들을 생성"""
    if start_date is None:
        start_date = datetime.now()
    
    end_date = start_date + timedelta(days=period_days)
    dates = []
    
    current = start_date
    while current <= end_date:
        if current.weekday() in weekdays:
            dates.append(current.date())
        current += timedelta(days=1)
    
    return dates
