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
from utils.llm_utils import LLMFactory, StreamHandler, ChatMemory
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
    - "방금 검색 결과 정보 게시에 올려줘"
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

    # 오늘의 할일 문자열 생성 - 간단하게 수정
    todays_goals_str = "없음"
    if todays_goals:
        goals_details = []
        for goal in todays_goals:
            start_time = goal.start_date.strftime("%H:%M")
            end_time = goal.end_date.strftime("%H:%M")
            importance = goal.importance if goal.importance else "미설정"
            memo = goal.memo if goal.memo else "미정"
            status = goal.status if goal.status else "미정"
           
            goal_detail = (
                f"일정 : {goal.title} / 시간 : {start_time}-{end_time} / 중요도: {importance} / 메모: {memo} / 상태: {status} "
            )
            goals_details.append(goal_detail)
        todays_goals_str = "\n".join(goals_details)

    # 미완료 목표 문자열 생성 - 간단하게 수정
    incomplete_goals_str = "없음"
    if incomplete_goals:
        goals_details = []
        for goal in incomplete_goals:
            deadline = goal.end_date.strftime("%Y-%m-%d")
            importance = goal.importance if goal.importance else "미정"
            memo = goal.memo if goal.memo else "미정"
            status = goal.status if goal.status else "미정"

            goal_detail = (
                f"- {goal.title} / 마감: {deadline} / 중요도: {importance} / 메모: {memo} / 상태: {status} "
            )
            goals_details.append(goal_detail)
        incomplete_goals_str = "\n".join(goals_details)

    return f"""
    {profile.get("content", "")}
    
    오늘의 할일:
    {todays_goals_str}
    
    미완료된 목표:
    {incomplete_goals_str}

    
    {profile.get('consultant_style', '')}
    """


# 세션 ID 생성 (앱 시작시)
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# ChatMemory 초기화
memory = ChatMemory(st.session_state.session_id)

# 시스템 메시지 추가 (처음 한 번만)
if not memory.get_messages():
    memory.add_message("system", generate_system_message())

# 이전 메시지 표시 (시스템 메시지 제외)
messages_container = st.container()
with messages_container:
    # 대화 내용 표시
    for (
        msg
    ) in (
        memory.get_display_messages()
    ):  # get_messages() 대신 get_display_messages() 사용
        with st.chat_message(
            "user" if isinstance(msg, HumanMessage) else "assistant"
        ):
            st.write(msg.content)

# 대화 저장 버튼 추가 (컨테이너 아래에)
if st.button("💾 대화 내용 저장"):
    try:
        # 현재 시간을 제목에 포함
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        title = f"AI 상담 기록 ({current_time})"

        # 전체 대화 컨텍스트 포함하여 저장
        context = ""
        messages = memory.get_messages()
        for msg in messages[1:]:  # 시스템 메시지 제외
            if isinstance(msg, HumanMessage):
                context += f"\n사용자: {msg.content}\n"
            elif isinstance(msg, AIMessage):
                context += f"\nAI: {msg.content}\n"

        # board 테이블에 'chat' 타입으로 저장
        add_post(
            board_type="chat",
            title=title,
            content=context.strip(),  # user_id 제거 (함수 내부에서 처리됨)
        )
        st.success("전체 대화 내용이 저장되었습니다.")
    except Exception as e:
        st.error(f"저장 중 오류가 발생했습니다: {str(e)}")

# 사용자 입력 처리
if prompt := st.chat_input("AI 컨설턴트에게 메시지를 보내세요"):
    # 사용자 메시지 표시
    with st.chat_message("user"):
        st.write(prompt)

    # 일반 대화 처리
    chat_container = st.chat_message("assistant")
    stream_handler = StreamHandler(chat_container)

    # LLM 응답 생성
    assistant_response = LLMFactory.get_response(
        st.session_state.selected_model,
        generate_system_message(),
        prompt,
        st.session_state.session_id,
        stream_handler=stream_handler,
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

# 세션 상태에 선택된 모델 저장 (기본값을 Claude-3-Haiku로 설정)
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
