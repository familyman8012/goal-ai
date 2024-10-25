import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from database import get_goals, get_categories, delete_goal

st.title("진행중/완료 목표 목록")

# 전체 목표 데이터 가져오기
goals_df = get_goals()

if goals_df.empty:
    st.info("등록된 목표가 없습니다. '새 목표 추가'에서 목표를 추가해보세요!")
else:
    # 먼저 필터링된 데이터프레임들을 생성
    current_time = datetime.now()

    # 각 기간별 필터링된 데이터프레임 미리 생성
    filtered_dfs = {
        "전체": goals_df,
        "오늘": goals_df[
            # 오늘 시작하는 목표
            (
                (
                    pd.to_datetime(goals_df["start_date"]).dt.date
                    == current_time.date()
                )
            )
            |
            # 오늘 끝나는 목표
            (
                (
                    pd.to_datetime(goals_df["end_date"]).dt.date
                    == current_time.date()
                )
            )
            |
            # 현재 진행 중인 목표
            (
                (pd.to_datetime(goals_df["start_date"]) <= current_time)
                & (pd.to_datetime(goals_df["end_date"]) >= current_time)
            )
        ],
        "1주": goals_df[
            (
                (pd.to_datetime(goals_df["start_date"]) >= current_time)
                & (
                    pd.to_datetime(goals_df["start_date"])
                    <= current_time + timedelta(days=7)
                )
            )
            | (
                (pd.to_datetime(goals_df["end_date"]) >= current_time)
                & (
                    pd.to_datetime(goals_df["end_date"])
                    <= current_time + timedelta(days=7)
                )
            )
            | (
                (pd.to_datetime(goals_df["start_date"]) <= current_time)
                & (pd.to_datetime(goals_df["end_date"]) >= current_time)
            )
        ],
        "1개월": goals_df[
            (
                (pd.to_datetime(goals_df["start_date"]) >= current_time)
                & (
                    pd.to_datetime(goals_df["start_date"])
                    <= current_time + timedelta(days=30)
                )
            )
            | (
                (pd.to_datetime(goals_df["end_date"]) >= current_time)
                & (
                    pd.to_datetime(goals_df["end_date"])
                    <= current_time + timedelta(days=30)
                )
            )
            | (
                (pd.to_datetime(goals_df["start_date"]) <= current_time)
                & (pd.to_datetime(goals_df["end_date"]) >= current_time)
            )
        ],
        "1년": goals_df[
            (
                (pd.to_datetime(goals_df["start_date"]) >= current_time)
                & (
                    pd.to_datetime(goals_df["start_date"])
                    <= current_time + timedelta(days=365)
                )
            )
            | (
                (pd.to_datetime(goals_df["end_date"]) >= current_time)
                & (
                    pd.to_datetime(goals_df["end_date"])
                    <= current_time + timedelta(days=365)
                )
            )
            | (
                (pd.to_datetime(goals_df["start_date"]) <= current_time)
                & (pd.to_datetime(goals_df["end_date"]) >= current_time)
            )
        ],
    }

    # 카테고리 필터를 탭 위에 배치
    categories_df = get_categories()
    category_options = ["전체"] + categories_df["name"].tolist()
    selected_category = st.selectbox("카테고리 필터", category_options)

    # 선택된 카테고리에 따라 모든 탭의 데이터 필터링
    if selected_category != "전체":
        category_id = categories_df[
            categories_df["name"] == selected_category
        ].iloc[0]["id"]
        for period in filtered_dfs:
            filtered_dfs[period] = filtered_dfs[period][
                filtered_dfs[period]["category_id"] == category_id
            ]

    tabs = st.tabs(list(filtered_dfs.keys()))

    for tab, (period, filtered_df) in zip(tabs, filtered_dfs.items()):
        with tab:
            # 진행 중인 목표
            st.subheader("진행 중인 목표")
            incomplete_goals = filtered_df[filtered_df["status"] != "완료"]
            if incomplete_goals.empty:
                st.info("진행 중인 목표가 없습니다.")
            else:
                for idx, goal in incomplete_goals.iterrows():
                    start_date = pd.to_datetime(goal["start_date"]).strftime(
                        "%Y-%m-%d"
                    )

                    # 목표 제목과 삭제 버튼을 나란히 배치하기 위한 컬럼 생성
                    col1, col2 = st.columns([6, 1])

                    with col1:
                        unique_key = f"incomplete_{goal['id']}_{period}_{idx}"
                        if st.button(
                            f"📌 {goal['title']} ({start_date})",
                            key=unique_key,
                        ):
                            st.query_params["goal_id"] = str(goal["id"])
                            st.switch_page("pages/3_goal_detail.py")

                    with col2:
                        delete_key = f"delete_{goal['id']}_{period}_{idx}"
                        if st.button("✕", key=delete_key):
                            if delete_goal(goal["id"]):
                                st.success(
                                    f"'{goal['title']}' 목표가 삭제되었습니다."
                                )
                                st.rerun()
                            else:
                                st.error("목표 삭제 중 오류가 발생했습니다.")

            # 완료된 목표
            st.subheader("완료된 목표")
            complete_goals = filtered_df[filtered_df["status"] == "완료"]
            if complete_goals.empty:
                st.info("완료된 목표가 없습니다.")
            else:
                for idx, goal in complete_goals.iterrows():
                    start_date = pd.to_datetime(goal["start_date"]).strftime(
                        "%Y-%m-%d"
                    )
                    unique_key = f"complete_{goal['id']}_{period}_{idx}"
                    if st.button(
                        f"✅ {goal['title']} ({start_date})", key=unique_key
                    ):
                        st.query_params["goal_id"] = str(goal["id"])
                        st.switch_page("pages/3_goal_detail.py")
