import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import openai
from database import get_goals, get_goal_analysis, add_goal_analysis
from config import OPENAI_API_KEY

st.title("미달성 목표 분석")

# 전체 목표 데이터 가져오기
goals_df = get_goals()

if goals_df.empty:
    st.info("등록된 목표가 없습니다.")
else:
    current_time = datetime.now()

    # 각 기간별 미달성 목표 필터링
    filtered_dfs = {
        "어제": goals_df[
            (
                pd.to_datetime(goals_df["end_date"]).dt.date
                == (current_time - timedelta(days=1)).date()
            )
            & (goals_df["status"] != "완료")
        ],
        "지난 주": goals_df[
            (
                pd.to_datetime(goals_df["end_date"])
                >= (current_time - timedelta(days=7))
            )
            & (pd.to_datetime(goals_df["end_date"]) < current_time)
            & (goals_df["status"] != "완료")
        ],
        "지난 달": goals_df[
            (
                pd.to_datetime(goals_df["end_date"])
                >= (current_time - timedelta(days=30))
            )
            & (pd.to_datetime(goals_df["end_date"]) < current_time)
            & (goals_df["status"] != "완")
        ],
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
                        f"❌ {goal['title']} ({start_date}-{end_date})",
                        key=unique_key,
                    ):
                        st.query_params["goal_id"] = str(goal["id"])
                        st.switch_page("pages/3_goal_detail.py")

                # GPT 분석
                important_goals = filtered_df.nlargest(3, "importance")
                if not important_goals.empty:
                    # 분석할 목표 ID 목록
                    goal_ids = important_goals.index.tolist()

                    # 기존 분석 결과 확인
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
                        client = openai.OpenAI(api_key=OPENAI_API_KEY)
                        response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {
                                    "role": "system",
                                    "content": """당신은 사용자의 가장 친한 친구이자 라이프 코치입니다. 
                                    친근하고 따뜻한 어조로, 
                                    마치 친한 고객님에게 응원의 편지를 쓰듯이 메시지를 전달합니다.                                    
                            
                                    - 1. 2. 이런식의 나열하듯 딱딱한 말을 하지 않고 구어체로 편지를 쓰듯 전달합니다.
                                    - 희망적이고 긍정적인 메시지로 마무리합니다.
                                    - 어떻게 하면 실천을 할 수 있을지에 대한 실행지침도 알려줍니다. 이때 이번 실행지침을 알려준다고 언급하세요.
                                    - 고객님이기때문에 친근하고 긍정적이고 때로 위트있지만 정중함도 곁들입니다.
                                    - 적절하게 다양한 이모티콘을 섞어서 표현합니다.""",
                                },
                                {
                                    "role": "user",
                                    "content": f"""다음은 달성하지 못한 소중한 목표들이에요:\n{goals_text}\n
                                    이 목표들이 이뤄졌다면 어떤 멋진 변화들이 있었을지, 
                                    마치 친한 고객님에게 이야기하듯이 따뜻하게 이야기해주세요.
                                    구체적인 상황과 감정을 상상하면서, 앞으로의 가능성도 함께 이야기해주세요.""",
                                },
                            ],
                            temperature=0.8,
                        )
                        return response.choices[0].message.content

                    if existing_analysis:
                        # 기존 분석 결과 표시
                        st.write(existing_analysis.analysis_result)

                        if regenerate:  # 재생성 버튼이 클릭되었을 때
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
