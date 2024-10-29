import streamlit as st
from langchain_community.chat_message_histories import (
    StreamlitChatMessageHistory,
)

# 페이지 설정을 가장 먼저 해야 함
st.set_page_config(
    page_title="목표 달성 GPT",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",  # "expanded"에서 "collapsed"로 변경
    menu_items=None,
)

# CSS로 사이드바 버튼 숨기기
st.markdown(
    """
    <style>
        [data-testid="collapsedControl"] {
            visibility: hidden;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

import openai
from datetime import datetime, timedelta
from database import (
    add_goal,
    get_categories,
    add_category,
    add_recurring_goals,
    add_post,
    get_category_name,
    get_user_profile,
    get_todays_goals,
    get_incomplete_goals,
)
from config import OPENAI_API_KEY
from utils.llm_utils import LLMFactory, StreamHandler
import uuid
from utils.date_utils import parse_weekdays, generate_recurring_dates
from utils.pplx_utils import search_with_pplx
from utils.menu_utils import show_menu  # 메뉴 컴포넌트 import
import re
from utils.session_utils import clear_goal_session
from utils.auth_utils import login_required, init_auth
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


# 인증 초기화
init_auth()

# 로그인 체크 - 최상단에 배치
if not st.session_state.get(
    "authenticated", False
) or not st.session_state.get("user_id"):
    st.switch_page("pages/login.py")
    st.stop()

# 페이지 진입 시 세션 정리
clear_goal_session()

# 메뉴 표시
show_menu()

st.title("🎯 목표 달성 GPT")

# 사용자 정보와 로그아웃 버튼 제거 (show_menu에서 처리됨)
# 이 부분 삭제:
# col1, col2 = st.sidebar.columns([3,1])
# with col1:
#     st.markdown(f"👤 {st.session_state.username}")
# with col2:
#     if st.button("🚪"):
#         logout()
#         st.switch_page("pages/login.py")

# 사용법 expander 추가
with st.expander("📖 사용법 보기"):
    st.markdown(
        """
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
    """
    )


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
            category = (
                "미분류"
                if not goal.category_id
                else get_category_name(goal.category_id)
            )
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
            category = (
                "미분류"
                if not goal.category_id
                else get_category_name(goal.category_id)
            )
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
    st.session_state.messages = []
    # 시스템 메시지는 history_key에 저장됨

# 세션 ID 생성 (앱 시작시)
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# 메시지 기록 키 생성
history_key = f"chat_history_{st.session_state.session_id}"

# 메시지 기록 초기화
if history_key not in st.session_state:
    st.session_state[history_key] = StreamlitChatMessageHistory(
        key=history_key
    )
    # 시스템 메시지 추가
    st.session_state[history_key].add_ai_message(generate_system_message())

# 이전 메시지 표시 (시스템 메시지 제외)
for msg in st.session_state[history_key].messages[1:]:  # 시스템 메시지 제외
    # AIMessage와 HumanMessage 객체 처리
    with st.chat_message(
        "user" if isinstance(msg, HumanMessage) else "assistant"
    ):
        st.write(msg.content)

# 사용자 입력 처리
if prompt := st.chat_input("AI 컨설턴트에게 메시지를 보내세요"):
    # 사용자 메시지 표시
    with st.chat_message("user"):
        st.write(prompt)

    # 사용자 메시지 저장 (HumanMessage 사용)
    st.session_state[history_key].add_user_message(prompt)

    # 일반 대화 처리
    chat_container = st.chat_message("assistant")
    stream_handler = StreamHandler(chat_container)

    assistant_response = LLMFactory.get_response(
        st.session_state.selected_model,
        generate_system_message(),  # 시스템 메시지 새로 생성
        prompt,
        st.session_state.session_id,
        stream_handler=stream_handler,
    )

    # AI 응답 저장 (AIMessage 사용)
    st.session_state[history_key].add_ai_message(assistant_response)

# 모델 선택 드다운 추가
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
