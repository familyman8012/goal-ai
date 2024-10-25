import streamlit as st
import openai
from datetime import datetime
from database import add_goal, get_categories, add_category, add_recurring_goals
from config import OPENAI_API_KEY
from utils.llm_utils import LLMFactory, StreamHandler  # StreamHandler 추가
import uuid
from utils.date_utils import parse_weekdays, generate_recurring_dates

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

# 사용자 입력
if prompt := st.chat_input("AI 컨설턴트에게 메시지를 보내세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

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

# 목표 추가 의도 확인 및 카테고리 파악
if prompt:
    intent_system_prompt = """사용자의 메시지에서 목표 추가 의도와 카테고리를 파악하세요. 
'커리어에 개발공부 추가해줘' 또는 '개발공부 추가해줘' 와 같은 형식이면 
'YES:목표내용:카테고리명' 형식으로, 
예를 들어 '커리어에 ts 공부 추가해줘'는 'YES:ts 공부:커리어'로, 
'ts 공부 추가해줘'는 'YES:ts 공부:전체'로,
'매주 화 목 토요일에 운동하기'와 같은 정기적인 일정은 'RECURRING:운동하기:전체'로,
목표 추가 의도가 없으면 'NO'로만 답하세요. 
단, '추가해줘'라는 단어가 있어야만 목표 추가로 인식합니다."""

    # single_get_response 사용으로 변경 (컨텍스트가 필요없는 단일 요청이므로)
    intent_response = LLMFactory.single_get_response(
        st.session_state.selected_model, intent_system_prompt, prompt
    )

    if intent_response.startswith("RECURRING:"):
        parts = intent_response.split(":")
        goal_title = parts[1].strip()
        category_name = parts[2].strip()
        
        # 요일 파싱
        weekdays = parse_weekdays(prompt)
        if weekdays:
            # 날짜 생성
            dates = generate_recurring_dates(weekdays)
            
            # 카테고리 처리
            category_id = None
            if category_name != "전체":
                category_match = categories_df[categories_df["name"] == category_name]
                if not category_match.empty:
                    category_id = category_match.iloc[0]["id"]
                else:
                    new_category = add_category(category_name)
                    category_id = new_category.id
            
            # 정기 목표 추가
            add_recurring_goals(
                title=goal_title,
                dates=dates,
                category_id=category_id
            )
            
            st.success(f"'{goal_title}'이(가) {len(dates)}개의 날짜에 추가되었습니다!")
            
    elif intent_response.startswith("YES:"):
        parts = intent_response.split(":")
        goal_title = parts[1].strip()
        category_name = parts[2].strip()

        # 카테고리 처리
        categories_df = get_categories()
        category_id = None
        if category_name != "전체":
            category_match = categories_df[
                categories_df["name"] == category_name
            ]
            if not category_match.empty:
                category_id = category_match.iloc[0]["id"]
            else:
                # 새 카테고리 추가
                new_category = add_category(category_name)
                category_id = new_category.id

        # GPT 응답
        chat_container = st.chat_message("assistant")
        stream_handler = StreamHandler(chat_container)

        # 날짜 확인을 위한 전용 시스템 프롬프트
        date_system_prompt = """
        사용자의 메시지에서 목표의 시작일과 종료일을 파악하세요.
        날짜가 언급되어 있다면 'START:YYYY-MM-DD,END:YYYY-MM-DD' 형식으로,
        없다면 'DEFAULT'로 응답하세요.
        """

        date_response = LLMFactory.single_get_response(
            st.session_state.selected_model,
            date_system_prompt,
            prompt,
        )

        if date_response == "DEFAULT":
            start_date = datetime.now()
            end_date = start_date
        else:
            try:
                start_str = (
                    date_response.split(",")[0].replace("START:", "").strip()
                )
                end_str = (
                    date_response.split(",")[1].replace("END:", "").strip()
                )

                # 날짜 형식 검증
                if not (
                    start_str.replace("-", "").isdigit()
                    and end_str.replace("-", "").isdigit()
                ):
                    start_date = datetime.now()
                    end_date = start_date
                else:
                    start_date = datetime.strptime(start_str, "%Y-%m-%d")
                    end_date = datetime.strptime(end_str, "%Y-%m-%d")
            except (ValueError, IndexError):
                start_date = datetime.now()
                end_date = start_date

        # 목표 제목 정리
        clean_title = (
            goal_title.replace("내일", "")
            .replace("오늘", "")
            .replace("다음주", "")
            .replace("다음달", "")
            .replace("다음 주", "")
            .replace("다음 달", "")
            .replace("이번주", "")
            .replace("이번달", "")
            .replace("이번 주", "")
            .replace("이번 달", "")
            .strip()
        )
        clean_title = (
            clean_title.replace("추가해줘", "").strip()
        )

        # AI 응답 생성
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

        # 목표 추가
        add_goal(
            title=clean_title,
            start_date=start_date,
            end_date=end_date,
            category_id=category_id,
        )
        st.success(
            f"'{clean_title}'이(가) 목표로 추가되었습니다! 상세 내용은"
            " 목표 목록에서 설정할 수 있습니다."
        )

    else:
        # 일반 대화
        chat_container = st.chat_message("assistant")  # 컨테이너를 직접 생성
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
