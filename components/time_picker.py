import streamlit.components.v1 as components
import os

def time_picker(value=None, key=None):
    """커스텀 시간 선택기 컴포넌트"""
    
    # HTML 파일 경로
    COMPONENT_PATH = os.path.join(os.path.dirname(__file__), "time_picker.html")
    
    # HTML 파일이 없으면 생성
    if not os.path.exists(COMPONENT_PATH):
        with open(COMPONENT_PATH, "w", encoding="utf-8") as f:
            f.write("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Time Picker</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css">
    <style>
        .time-picker-container {
            width: 100%;
            margin: 5px 0;
        }
        input {
            width: 100%;
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="time-picker-container">
        <input id="timePicker" type="text" placeholder="시간을 선택하거나 입력하세요 (예: 14:30)">
    </div>
    <script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>
    <script>
        const fp = flatpickr("#timePicker", {
            enableTime: true,
            noCalendar: true,
            dateFormat: "H:i",
            time_24hr: true,
            defaultDate: "%s",
            onChange: function(selectedDates, dateStr, instance) {
                const event = new CustomEvent("streamlit:setComponentValue", {
                    detail: dateStr
                });
                window.parent.document.dispatchEvent(event);
            }
        });
    </script>
</body>
</html>
            """ % (value if value else ""))
    
    # 컴포넌트 렌더링
    return components.html(
        open(COMPONENT_PATH, "r", encoding="utf-8").read(),
        height=70,
        key=key
    )
