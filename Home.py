import streamlit as st
import openai
from datetime import datetime, timedelta
from database import add_goal, get_categories, add_category, add_recurring_goals, add_post, get_category_name, get_user_profile, get_todays_goals, get_incomplete_goals
from config import OPENAI_API_KEY
from utils.llm_utils import LLMFactory, StreamHandler
import uuid
from utils.date_utils import parse_weekdays, generate_recurring_dates
from utils.pplx_utils import search_with_pplx
from utils.menu_utils import show_menu  # 메뉴 컴포넌트 import
import re
from utils.session_utils import clear_goal_session

# 페이지 설정 전에 세션 정리
clear_goal_session()

# 페이지 설정
st.set_page_config(
    page_title="목표 달성 GPT",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items=None  # 기본 메뉴 완전히 제거
)

# 메뉴 표시
show_menu()

st.title("목표 달성 GPT")

# 사용법 expander 추가
with st.expander("📖 사용법 보기"):
    st.markdown("""
    ## 💬 기본 대화 기능
    AI 컨설턴트와 자연스러운 대화를 나눌 수 있습니다.

    ## 🔍 검색 기능
    ```
    시:
    - "2024년 개봉 영화 검색해줘"
    - "파이썬 강의 추천 검색해줘"
    ```

    ### 검색 결과 저장
    ```
    예시:
    - "방금 검색 결과 정보 게시판에 올려줘"
    - "방금 검색 결과 제목은 2024 상반기 개봉 영화로 정보 게시판에 올려줘"
    ```

    ### 일반 정보 저장
    ```
    예시:
    - "(올리고 싶은 내용)을 정보 게시판에 올려줘"
    - "제목은 ooo으로 ooo를 정보 게시판에 올려줘"
    ```

    ### 목표 추가
    ```
    예시:
    - "커리어(카테고리)에 타입스크립트 공부 추가해줘"
    - "운동(카테고리) 목표에 매주 수요일 저녁 요가 추가해줘"
    - "다음 달까지 책 3권 읽기 목표 추가해줘"
    - "내일 취미에 모임하나 추가해줘"            
    ```

    ### 반복 목표 설정
    ```
    예시:
    - "매주 월,수,금 아침 러닝하기 추가해줘"
    - "매주 화요일 저녁 스터디 참석 추가해줘"  
    ```

    ### 아이디어 게시판
    ```
    예시:
    - "내일 모임하나 신청해야겠다를 아이디어 게시판에 올려줘"
    - "제목은 모임 신청으로 내일 모임하나 신청해야겠다를 아이디어 게시판에 올려줘"
    ```
    """)

# Tool 관련 코드 제거
def generate_system_message():
    profile = get_user_profile()
    todays_goals = get_todays_goals()
    incomplete_goals = get_incomplete_goals()
    
    # 오늘의 할일 문자열 생성
    todays_goals_str = "없음"
    if todays_goals:
        goals_details = []
        for goal in todays_goals:
            start_time = goal.start_date.strftime("%H:%M")
            end_time = goal.end_date.strftime("%H:%M")
            category = "미분류" if not goal.category_id else get_category_name(goal.category_id)
            importance = goal.importance if goal.importance else "미설정"
            
            goal_detail = (
                f"- {goal.title}\n"
                f"  📅 {start_time}-{end_time}\n"
                f"  📁 카테고리: {category}\n"
                f"  ⭐ 중요도: {importance}\n"
                f"  📝 메모: {goal.memo if goal.memo else '없음'}"
            )
            goals_details.append(goal_detail)
        todays_goals_str = "\n\n".join(goals_details)
    
    # 미완료 목표 문자열 생성
    incomplete_goals_str = "없음"
    if incomplete_goals:
        goals_details = []
        for goal in incomplete_goals:
            category = "미분류" if not goal.category_id else get_category_name(goal.category_id)
            importance = goal.importance if goal.importance else "미설정"
            deadline = goal.end_date.strftime("%Y-%m-%d %H:%M")
            
            goal_detail = (
                f"{goal.title}\n"
                f"마감: {deadline}\n"
                f"카테고리: {category}\n"
                f"중요도: {importance}\n"
                f"메모: {goal.memo if goal.memo else '없음'}"
            )
            goals_details.append(goal_detail)
        incomplete_goals_str = "\n\n".join(goals_details)
    
    return f"""당신은 사용자의 AI 컨설턴트입니다. 
    당신은 세계 최고의 동기부여가입니다.
    
    {profile.get("content", "")}
    
    오늘의 할일:
    {todays_goals_str}
    
    미완료된 목표:
    {incomplete_goals_str}
    
    첫 인사시, 오늘의 할일과 미완료된 목표를 언급하고,
    오늘의 할일에 대해서는 격려와 응원을,
    미완료된 목표에 대해서는 주의를 환기시켜주세요.
    
    {profile.get('consultant_style', '')}
    """

# 채팅 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": generate_system_message()
        }
    ]

# 이전 메시지 표시
for message in st.session_state.messages[1:]:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# 사용자 입력 처리 부분 수정
if prompt := st.chat_input("AI 컨설턴트에게 메시지를 보내세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # 검색 결과를 세션에 저장
    if "last_search_result" not in st.session_state:
        st.session_state.last_search_result = None
        st.session_state.last_search_query = None

    # 정확히 '검색해줘'로 끝나는 경우에만 PPLX API 호출
    if prompt.endswith("검색해줘"):
        search_query = prompt[:-4].strip()  # "검색해줘" 제거
        search_result = search_with_pplx(search_query)
        
        # 검색 결과를 세션 상태에 저장
        st.session_state.last_search_result = search_result
        st.session_state.last_search_query = search_query
        
        chat_container = st.chat_message("assistant")
        chat_container.markdown(search_result)
        
        # 사용자의 질문과 검색 결과를 대화 컨텍스트에 추가
        st.session_state.messages.append({"role": "assistant", "content": search_result})
        
        # 검색 결과를 시스템 메시지에 추가하여 컨텍스트 유지
        context_update = f"""이전 검색 결과 정보:
        검색어: {search_query}
        결과: {search_result}
        
        이 정보를 참고하여 대화를 이어나가주세요."""
        
        st.session_state.messages[0]["content"] += "\n\n" + context_update
    
    # 정보 게시판에 올리기 요청 처리
    elif ("정보 게시판에" in prompt or "정보게시판에" in prompt) and "올려줘" in prompt:
        chat_container = st.chat_message("assistant")
        
        # 제목 추출 로직
        title = None
        content = prompt  # 전체 내용을 저장
        
        # "제목은 X로" 형식 확인
        if "제목은" in prompt and "로" in prompt:
            title_start = prompt.find("제목은") + 3
            title_end = prompt.find("로", title_start)
            if title_start != -1 and title_end != -1:
                title = prompt[title_start:title_end].strip()
                # 제목 부분을 내용에서 제거
                content = content.replace(f"제목은 {title}로", "")
        
        # "정보 게시판에 올려줘" 부분 제거
        content = content.replace("정보 게시판에 올려줘", "").replace("정보게시판에 올려줘", "").strip()
        
        # 검색 결과가 있는 경우와 일반 텍스트를 올리는 경우 구분
        if st.session_state.get("last_search_result"):
            content_to_save = st.session_state.last_search_result
            title_to_save = title or st.session_state.last_search_query
            
            # 저장 후 검색 결과 초기화
            st.session_state.last_search_result = None
            st.session_state.last_search_query = None
        else:
            content_to_save = content
            title_to_save = title or "새운 정보"  # 제목이 없는 경우 기본값
        
        try:
            add_post(title_to_save, content_to_save, "info")
            chat_container.markdown("✅ 정보가 게��판에 저장되었습니다.")
        except Exception as e:
            chat_container.markdown(f"❌ 게시판 저장 중 오류가 발생했습니다: {str(e)}")
    
    # 아이디어 게시판에 올리기 요청 처리
    elif "아이디어 게시판에" in prompt and "올려줘" in prompt:
        chat_container = st.chat_message("assistant")
        
        # 제목 추출 로직
        title = "새로운 아이디어"  # 기본값
        content = prompt  # 전체 내용을 저장
        
        if "제목은" in prompt and "로" in prompt:
            title_start = prompt.find("제목은") + 3
            title_end = prompt.find("로", title_start)
            if title_start != -1 and title_end != -1:
                title = prompt[title_start:title_end].strip()
                # 제목 부분을 내용에서 제거
                content = content.replace(f"제목은 {title}로", "")
        
        # "아이디어 게시판에 려줘" 부분 제거
        content = content.replace("아이디어 게시판에 올려줘", "").strip()
        
        try:
            add_post(title, content, "idea")
            chat_container.markdown("✅ 아이디어가 시판에 저장되었습니다.")
        except Exception as e:
            chat_container.markdown(f"❌ 게시판 저장 중 오류가 발생했습니다: {str(e)}")
    
    else:
        # 날짜 처리를 위한 함수 추가
        def parse_time_from_text(text):
            """텍스트에서 시간 정를 추출하여 24시간 형식으로 반환"""
            time_pattern = r'(\d{1,2})시'
            match = re.search(time_pattern, text)
            if match:
                hour = int(match.group(1))
                # 12시 이하는 오후로 간주 (오전/오후가 명시되지 않은 경우)
                if hour <= 12:
                    hour += 12
                return datetime.strptime(f"{hour}:00", "%H:%M").time()
            # 시간이 지정되지 않은 경우 오전 10시 반환
            return datetime.strptime("10:00", "%H:%M").time()

        def parse_date_from_text(text):
            """텍스트에서 날짜 정보를 추출"""
            today = datetime.now().date()
            
            # "오늘" 처리
            if "오늘" in text:
                return today
            
            # "내일" 처리
            if "내일" in text:
                return today + timedelta(days=1)
                
            # "내일모레" 처리
            if "내일모레" in text:
                return today + timedelta(days=2)
                
            # "다음주" 처
            if "다음주" in text:
                return today + timedelta(days=7)
                
            # 특정 날짜 처리 (예: "10월 28일")
            date_pattern = r'(\d{1,2})월\s*(\d{1,2})일'
            match = re.search(date_pattern, text)
            if match:
                month, day = map(int, match.groups())
                year = today.year
                # 지정된 날짜가 오늘보다 이전이면 내년으로 설정
                try:
                    date = datetime(year, month, day).date()
                    if date < today:
                        date = datetime(year + 1, month, day).date()
                    return date
                except ValueError:
                    return today
                    
            return today

        # 목표 추가 요청 처리 부분 수정
        if "추가해줘" in prompt:
            # 카테고리 추출
            category_name = None
            category_id = None
            
            # 카테고리 패턴 확인 (예: "커리어에", "운동에서", "취미로")
            category_pattern = r'([가-힣]+)(?:에|에서|로|의)\s'
            category_match = re.search(category_pattern, prompt)
            if category_match:
                category_name = category_match.group(1)
                # 카테고리 데이터 가져오기
                categories_df = get_categories()
                category_match_df = categories_df[categories_df['name'] == category_name]
                if not category_match_df.empty:
                    category_id = category_match_df.iloc[0]['id']
            
            # 목표 제목 추출 (날짜, 시간, 카테고리 관련 텍스트와 "추가해줘" 제외)
            title = prompt.replace("추가해줘", "").strip()
            if category_name:
                title = re.sub(f'{category_name}(?:에|에서|로|의)\\s', '', title)
            title = re.sub(r'(오늘|내일|내일모레|다음주|\d+월\s*\d+일에?|\d+시에?)\s*', '', title).strip()
            
            # 날짜와 시간 파싱
            target_date = parse_date_from_text(prompt)
            target_time = parse_time_from_text(prompt)
            
            try:
                # datetime 객체 생성
                target_datetime = datetime.combine(target_date, target_time)
                
                # 목표 추가
                add_goal(
                    title=title,
                    start_date=target_datetime,
                    end_date=target_datetime,
                    status="진행 전",
                    category_id=category_id
                )
                
                chat_container = st.chat_message("assistant")
                category_text = f" ({category_name} 카테고리)" if category_name else ""
                success_message = f"✅ '{title}'{category_text} 목표가 {target_datetime.strftime('%Y년 %m월 %d일 %H시 %M분')}에 추가되었습니다!"
                chat_container.success(success_message)
                
                # 대화 기록에 추가
                st.session_state.messages.append({"role": "assistant", "content": success_message})
                
            except Exception as e:
                chat_container = st.chat_message("assistant")
                error_message = f"❌ 목표 추가 중 오류가 발생했습니다: {str(e)}"
                chat_container.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})
        
        else:
            # 기존의 일반 대화 처리 코드 부분을 수정
            chat_container = st.chat_message("assistant")
            stream_handler = StreamHandler(chat_container)
            
            assistant_response = LLMFactory.get_response(
                st.session_state.selected_model,
                st.session_state.messages[0]["content"],
                prompt,
                st.session_state.session_id,  # session_id 추가
                stream_handler=stream_handler,
            )

            st.session_state.messages.append(
                {"role": "assistant", "content": assistant_response}
            )

# 모델 선택 드롭다운 추가
st.sidebar.title("AI 모델 설정")
model_options = {
    "GPT-4o": "gpt-4o",
    "GPT-4o-mini": "gpt-4o-mini",
    "Claude-3.5-Sonnet": "claude-3-5-sonnet-20240620",
    "Claude-3-Haiku": "claude-3-haiku-20240307",
    "Gemini-Pro": "gemini-1.5-pro-latest",
    "Gemini-Flash": "gemini-1.5-flash-latest",
}

# 션 상태에 선택된 모델 저장 (기본값을 Claude-3-Haiku로 정)
if "selected_model" not in st.session_state:
    st.session_state.selected_model = model_options["Claude-3-Haiku"]

selected_model = st.sidebar.selectbox(
    "사용할 AI 모델을 선택하세요",
    list(model_options.keys()),
    index=list(model_options.keys()).index(
        "Claude-3-Haiku"
    ),  # 기본값을 Gemini-Pro로 설정
)

# 선택된 모델 변경되었을 때만 업데이트
if st.session_state.selected_model != model_options[selected_model]:
    st.session_state.selected_model = model_options[selected_model]

# 세션 ID 생성 (앱 시작시)
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
















