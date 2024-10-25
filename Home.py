import streamlit as st
import openai
from datetime import datetime
from database import add_goal, get_categories, add_category, add_recurring_goals
from config import OPENAI_API_KEY
from utils.llm_utils import LLMFactory, StreamHandler  # StreamHandler 추가
import uuid
from utils.date_utils import parse_weekdays, generate_recurring_dates
from utils.pplx_utils import search_with_pplx

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
            4. 사용자가 직접 목표 추가를 요청할 때는 공감과 지지를 보내주세요.
            5. 용자가 언급하는 날짜를 파악하여 목표의 시작일과 종료일을 설정해주세요.
            
            이전 대화 내용을 잘 기억하고 참조하여, 마치 실제 상담사처럼 자연스러운 대화를 이어나가세요.""",
        }
    ]

# 이전 메시지 표시
for message in st.session_state.messages[1:]:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# 사용자 입력 처리
if prompt := st.chat_input("AI 컨설턴트에게 메시지를 보내세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # 정확히 '검색해줘'로 끝나는 경우에만 PPLX API 호출
    if prompt.endswith("검색해줘"):
        search_query = prompt[:-4].strip()  # "검색해줘" 제거
        search_result = search_with_pplx(search_query)
        
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
    
    else:
        # 일반 대화 처리
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

# 션 상태에 선택된 모델 저장 (기본값을 Claude-3-Haiku로 설정)
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
