import streamlit as st
import openai
from datetime import datetime, timedelta
from database import add_goal, get_categories, add_category, add_recurring_goals, add_post
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
st.markdown(
    """
<p style='color: gray; font-size: 0.9em;'>
💡 사용법: "커리어에 ts 공부 추가해줘" 와 같이 자연스럽게 대화해보세요.
</p>
""",
    unsafe_allow_html=True,
)

# 채팅 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": f"""당신은 세계 최고의 라이프 컨설턴트입니다. 
            현재 날짜는 {datetime.now().strftime('%Y년 %m월 %d일')}입니다.
            
            다음 지침을 따라주세요:
            1. 사용자의 이야기를 경청하고 공감하며, 대화의 맥락을 잘 이해합니다.
            2. 사용자의 고민이나 이야기에서 목표로 발전시킬만한 내용이 있다면,
               자연스게 "그럼 [구체적인 목표]를 목표로 추가해보는 건 어떠세요?" 라고 제안합니다.
            3. 단, 모든 대화에서 목표를 제안하지 않고, 대화의 흐름을 보며 적절한 때에만 제안합니다.
            4. 사용자가 직접 목표 추가를 요청할 때는 공감과 ��지를 보내주세요.
            5. 용자가 언급하는 날짜를 파악하여 목표의 시작일과 종료일을 설정해주세요.
            
            이전 대화 내용을 잘 기억하고 참조하여, 마치 실제 상담사처럼 자연스러운 대화를 이어나가세요.""",
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
    elif "정보 게시판에" in prompt and "올려줘" in prompt and st.session_state.get("last_search_result"):
        chat_container = st.chat_message("assistant")
        
        # 제목 추출 로직
        title = st.session_state.last_search_query  # 기본값으로 검색어 사용
        if "제목은" in prompt and "로" in prompt:
            title_start = prompt.find("제목은") + 3
            title_end = prompt.find("로", title_start)
            if title_start != -1 and title_end != -1:
                title = prompt[title_start:title_end].strip()
        
        try:
            add_post(title, st.session_state.last_search_result, "info")
            chat_container.markdown("✅ 검색 결과가 정보 게시판에 저장되었습니다.")
            
            # 저장 후 검색 결과 초기화
            st.session_state.last_search_result = None
            st.session_state.last_search_query = None
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
        
        # "아이디어 게시판에 올려줘" 부분 제거
        content = content.replace("아이디어 게시판에 올려줘", "").strip()
        
        try:
            add_post(title, content, "idea")
            chat_container.markdown("✅ 아이디어가 게시판에 저장되었습니다.")
        except Exception as e:
            chat_container.markdown(f"❌ 게시판 저장 중 오류가 발생했습니다: {str(e)}")
    
    else:
        # 날짜 처리를 위한 함수 추가
        def parse_date_from_text(text):
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
                
            # "다음주" 처리
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

        # 목표 추가 요청 처리
        if "추가해줘" in prompt:
            # 목표 제목 추출 (날짜 관련 텍스트와 "추가해줘" 제외)
            title = prompt.replace("추가해줘", "").strip()
            title = re.sub(r'(오늘|내일|내일모레|다음주|\d+월\s*\d+일에?)\s*', '', title).strip()
            
            # 날짜 파싱
            target_date = parse_date_from_text(prompt)
            
            try:
                # 목표 추가
                add_goal(
                    title=title,
                    start_date=target_date,
                    end_date=target_date,
                    status="진행 전"
                )
                
                chat_container = st.chat_message("assistant")
                success_message = f"✅ '{title}' 목표가 {target_date.strftime('%Y년 %m월 %d일')}에 추가되었습니다!"
                chat_container.success(success_message)
                
                # 대화 기록에 추가
                st.session_state.messages.append({"role": "assistant", "content": success_message})
                
            except Exception as e:
                chat_container = st.chat_message("assistant")
                error_message = f"❌ 목표 추가 중 오류가 발생했습니다: {str(e)}"
                chat_container.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})
        
        else:
            # 기존의 일반 대화 처리 코드...
            chat_container = st.chat_message("assistant")
            stream_handler = StreamHandler(chat_container)
            
            assistant_response = LLMFactory.get_response(
                st.session_state.selected_model,
                st.session_state.messages[0]["content"],
                prompt,
                st.session_state.session_id,
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

# 선택된 모델이 변경되었을 때만 업데이트
if st.session_state.selected_model != model_options[selected_model]:
    st.session_state.selected_model = model_options[selected_model]

# 세션 ID 생성 (앱 시작시)
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
