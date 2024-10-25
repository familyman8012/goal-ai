import streamlit as st
import openai
from datetime import datetime
from database import add_goal, get_categories, add_category
from config import OPENAI_API_KEY

st.title("AI 라이프 컨설턴트와 대화")
st.markdown(
    """
<p style='color: gray; font-size: 0.9em;'>
💡 사용법: "커리어 카테고리에 개발공부 목표로 추가해줘" 와 같이 자연스럽게 대화해보세요.
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
               자연스럽게 "그럼 [구체적인 목표]를 목표로 추가해보는 건 어떠세요?" 라고 제안합니다.
            3. 단, 모든 대화에서 목표를 제안하지 않고, 대화의 흐름을 보며 적절한 때에만 제안합니다.
            4. 사용자가 직접 목표 추가를 요청할 때는 공감과 지지를 보내주세요.
            5. 사용자가 언급하는 날짜를 파악하여 목표의 시작일과 종료일을 설정해주세요.
            
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

    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    # 목표 추가 의도 확인 및 카테고리 파악
    # 이전 대화 내용을 포함하여 전송
    all_messages = st.session_state.messages + [
        {
            "role": "system",
            "content": (
                "사용자의 메시지에서 목표 추가 의도와 카테고리를 파악하세요. "
                "'커리어 카테고리에 개발공부 하는 거 목표로 추가해줘' 와 같은 형식이면 "
                "'YES:목표내용:카테고리명' 형식으로, "
                "'개발 공부하는 거 목표로 해줘' 와 같이 카테고리가 없으면 "
                "'YES:목표내용:전체' 형식으로, "
                "목표 추가 의도가 없으면 'NO'로만 답하세요."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    goal_intent_check = client.chat.completions.create(
        model="gpt-4o",  # gpt-4 -> gpt-4o로 다시 수정
        messages=all_messages,
        temperature=0,
    )

    intent_response = goal_intent_check.choices[0].message.content

    if intent_response.startswith("YES:"):
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
        with st.chat_message("assistant"):
            response = client.chat.completions.create(
                model="gpt-4o",  # gpt-4 -> gpt-4o로 다시 수정
                messages=st.session_state.messages,
                temperature=0.7,
            )

            assistant_response = response.choices[0].message.content
            st.session_state.messages.append(
                {"role": "assistant", "content": assistant_response}
            )
            st.write(assistant_response)

            if intent_response.startswith("YES:"):
                goal_title = intent_response.split("YES:")[1].strip()
                # 날짜 관련 단어들 제거
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
                # 목표 추가/목표로 등의 문구 제거
                clean_title = (
                    clean_title.replace("목표 추가", "")
                    .replace("목표로", "")
                    .strip()
                )

                # 날짜 확인 시에도 이전 대화 내용 포함
                all_date_messages = st.session_state.messages + [
                    {
                        "role": "system",
                        "content": (
                            "현재 날짜는"
                            f" {datetime.now().strftime('%Y년 %m월 %d일')}입니다."
                            " 사용자의 메시지에서 언급된 날짜를 파악하여"
                            " 'START:YYYY-MM-DD,END:YYYY-MM-DD' 형식으로"
                            " 답변하세요. 날짜가 없다면 'DEFAULT'로"
                            " 답하세요."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ]

                date_check = client.chat.completions.create(
                    model="gpt-4o",  # gpt-4 -> gpt-4o로 다시 수정
                    messages=all_date_messages,
                    temperature=0,
                )

                date_response = date_check.choices[0].message.content

                if date_response == "DEFAULT":
                    start_date = datetime.now()
                    end_date = start_date
                else:
                    start_str = date_response.split(",")[0].replace(
                        "START:", ""
                    )
                    end_str = date_response.split(",")[1].replace("END:", "")
                    start_date = datetime.strptime(
                        start_str.strip(), "%Y-%m-%d"
                    )
                    end_date = datetime.strptime(end_str.strip(), "%Y-%m-%d")

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
        # 목표 추가 의도가 없는 경우의 일반 대화
        with st.chat_message("assistant"):
            response = client.chat.completions.create(
                model="gpt-4o",  # gpt-4 -> gpt-4o로 다시 수정
                messages=st.session_state.messages,
                temperature=0.7,
            )
            assistant_response = response.choices[0].message.content
            st.session_state.messages.append(
                {"role": "assistant", "content": assistant_response}
            )
            st.write(assistant_response)
