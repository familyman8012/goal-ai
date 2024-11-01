import streamlit as st
# 최상단에 배치
st.set_page_config(
    page_title="미달성 목표 분석",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items=None
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
    unsafe_allow_html=True
)
from datetime import datetime, timedelta
import pandas as pd
import openai
from database import get_goals, get_goal_analysis, add_goal_analysis
from config import OPENAI_API_KEY
from utils.llm_utils import LLMFactory, StreamHandler
import uuid
from utils.session_utils import clear_goal_session
from utils.auth_utils import login_required, init_auth
from utils.menu_utils import show_menu  # 추가
import pytz



# 메뉴 표시 추가
show_menu()

# 페이지 진입 시 세션 정리
clear_goal_session()

# 인증 초기화
init_auth()

# 로그인 체크
login_required()

# 상단에 uuid import 추가
# session_id 생성 (앱 시작시)
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# 전체 목표 데이터 가져오기
goals_df = get_goals()

if goals_df.empty:
    st.info("등록된 목표가 없습니다.")
else:
    current_time = pd.Timestamp.now(tz=pytz.timezone('Asia/Seoul'))

    # 각 기간별 미달성 목표 필터링
    filtered_dfs = {
        "어제": goals_df[
            (
                pd.to_datetime(goals_df["end_date"]).dt.tz_convert('Asia/Seoul').dt.date
                == (current_time - timedelta(days=1)).date()
            )
            & (goals_df["status"] != "완료")
        ].sort_values(by='start_date', ascending=False),
        
        "지난 주": goals_df[
            (
                pd.to_datetime(goals_df["end_date"]).dt.tz_convert('Asia/Seoul')
                >= (current_time - timedelta(days=7))
            )
            & (pd.to_datetime(goals_df["end_date"]).dt.tz_convert('Asia/Seoul') < current_time)
            & (goals_df["status"] != "완료")
        ].sort_values(by='start_date', ascending=False),
        
        "지난 달": goals_df[
            (
                pd.to_datetime(goals_df["end_date"]).dt.tz_convert('Asia/Seoul')
                >= (current_time - timedelta(days=30))
            )
            & (pd.to_datetime(goals_df["end_date"]).dt.tz_convert('Asia/Seoul') < current_time)
            & (goals_df["status"] != "완료")
        ].sort_values(by='start_date', ascending=False),
    }

    tabs = st.tabs(list(filtered_dfs.keys()))

    for tab, (period, filtered_df) in zip(tabs, filtered_dfs.items()):
        with tab:
            if filtered_df.empty:
                st.info(f"{period}에 미달성된 목표가 없습니다.")
            else:
                st.subheader(f"{period} 미달성 목표")
                for idx, goal in filtered_df.iterrows():
                    start_date = pd.to_datetime(goal["start_date"]).strftime(
                        "%Y-%m-%d"
                    )
                    end_date = pd.to_datetime(goal["end_date"]).strftime(
                        "%Y-%m-%d"
                    )
                    unique_key = f"incomplete_{goal['id']}_{period}_{idx}"
                    if st.button(
                        f"❌ {goal['title']} ({start_date}-{end_date})", key=unique_key
                    ):
                        try:
                            goal_id = int(goal["id"])
                            # 세션에 goal_id 저장
                            st.session_state.selected_goal_id = goal_id
                            st.switch_page("pages/3_goal_detail.py")
                        except Exception as e:
                            st.error(f"Error processing goal ID: {str(e)}")

                # GPT 분석
                important_goals = filtered_df.nlargest(3, "importance")
                if not important_goals.empty:
                    # 분석할 목표 ID 목록
                    goal_ids = important_goals.index.tolist()

                    # 기존 분석 결과 인
                    existing_analysis = get_goal_analysis(period, goal_ids)

                    # GPT 메시지 제목과 재생성 버튼을 나란히 배치
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.subheader("GPT 메세지")
                    with col2:
                        if existing_analysis:
                            regenerate = st.button(
                                "💫 새로운 메시지", key=f"regenerate_{period}"
                            )

                    def generate_analysis(goals_text):
                        system_prompt = """당신은 사용자의 가장 친한 친구이자 라이프 코치입니다. 
                        친근하고 따뜻한 어조로, 
                        마치 친한 고객님에게 응원의 편지를 쓰듯이 메시지를 전달합니다.                                    

                        - 1. 2. 이런식의 나열하듯 딱딱한 말을 하지 않고 구어체로 편지를 쓰듯 전달합니다.
                        - 희망적이고 긍정적인 메시지로 마무리합니다.
                        - 어떻게 하면 실천을 할 수 있을지에 대한 실행지침도 알려줍니다.
                        - 고객님이기때문에 친근하고 정적이고 때로 위트있지만 정중함도 곁들입니다.
                        - 적절하게 다양한 이모티콘을 섞어서 표현합니다."""

                        user_prompt = f"""다음은 달성하지 못한 소중한 목표들이에요:\n{goals_text}\n
                        이 목표들이 이뤄졌다면 어떤 멋진 변화들이 있었을지, 
                        마치 친한 고객님에게 이야기하듯이 따뜻하게 이야기해주세요.
                        구체적인 상황과 감정을 상상하면서, 앞으로의 가능성도 함께 이야기해주세요."""

                        # StreamHandler 초기화
                        chat_container = st.empty()
                        stream_handler = StreamHandler(chat_container)

                        return LLMFactory.get_response(
                            st.session_state.selected_model,
                            system_prompt,
                            user_prompt,
                            st.session_state.session_id,
                            stream_handler=stream_handler
                        )

                    if existing_analysis:
                        # 기존 분석 결과 표시
                        st.write(existing_analysis.analysis_result)

                        if regenerate:  # 재생성 버튼 클릭되었을 때
                            goals_text = "\n".join(
                                [
                                    f"- {row['title']} (중요도:"
                                    f" {row['importance']})"
                                    for _, row in important_goals.iterrows()
                                ]
                            )

                            # 새로운 분석 생성
                            new_analysis = generate_analysis(goals_text)

                            # DB에 새 분석 저장
                            add_goal_analysis(period, goal_ids, new_analysis)

                            # 새 분석 표시
                            st.write(new_analysis)

                            # 페이지 새로고침하여 최신 분석 표시
                            st.rerun()
                    else:
                        # 새로운 분석 필요
                        if st.button(
                            f"{period} 미달성 목표 분석",
                            key=f"analyze_{period}",
                        ):
                            goals_text = "\n".join(
                                [
                                    f"- {row['title']} (중요도:"
                                    f" {row['importance']})"
                                    for _, row in important_goals.iterrows()
                                ]
                            )

                            # 새로운 분석 생성
                            analysis_result = generate_analysis(goals_text)

                            # 분석 결과를 DB에 저장
                            add_goal_analysis(
                                period, goal_ids, analysis_result
                            )

                            # 분석 결과 표시
                            st.write(analysis_result)
