import streamlit as st
from datetime import datetime
from database import get_goals, update_goal, add_goal, get_categories
from config import GOAL_STATUS, IMPORTANCE_LEVELS

# URL parameter에서 goal_id를 가져옴 (experimental 제거)
goal_id = st.query_params.get("goal_id")

goals_df = get_goals()
goal = None

if goal_id:
    filtered_goals = goals_df[goals_df["id"] == int(goal_id)]
    if not filtered_goals.empty:
        goal = filtered_goals.iloc[0]
        st.title(f"목표 상세: {goal['title']}")
else:
    st.title("새 목표 추가")

# 입력 필드
title = st.text_input("목표", value="" if goal is None else goal["title"])

col1, col2 = st.columns(2)

with col1:
    default_start = datetime.now()
    start_date = st.date_input(
        "시작일",
        value=(
            goal["start_date"].date()
            if goal is not None and isinstance(goal["start_date"], datetime)
            else (
                goal["start_date"]
                if goal is not None and goal["start_date"] is not None
                else default_start
            )
        ),
    )

with col2:
    default_end = datetime.now()
    end_date = st.date_input(
        "종료일",
        value=(
            goal["end_date"].date()
            if goal is not None and isinstance(goal["end_date"], datetime)
            else (
                goal["end_date"]
                if goal is not None and goal["end_date"] is not None
                else default_end
            )
        ),
    )

trigger_action = st.text_input(
    "동기", value="" if goal is None else goal["trigger_action"]
)

importance = st.selectbox(
    "중요도",
    IMPORTANCE_LEVELS,
    index=(
        IMPORTANCE_LEVELS.index(goal["importance"])
        if goal is not None and goal["importance"] in IMPORTANCE_LEVELS
        else 4
    ),
)

memo = st.text_area("메모", value="" if goal is None else goal["memo"])

status = st.selectbox(
    "상태",
    GOAL_STATUS,
    index=(
        GOAL_STATUS.index(goal["status"])
        if goal is not None and goal["status"] in GOAL_STATUS
        else 0
    ),
)

# 카테고리 선택
categories_df = get_categories()
category_options = ["전체"] + categories_df["name"].tolist()
selected_category = st.selectbox(
    "카테고리",
    category_options,
    index=(
        category_options.index(
            categories_df[categories_df["id"] == goal["category_id"]].iloc[0][
                "name"
            ]
        )
        if goal is not None and goal["category_id"] is not None
        else 0
    ),
)

# 선택된 카테고리의 ID 찾기
category_id = None
if selected_category != "전체":
    category_match = categories_df[categories_df["name"] == selected_category]
    if not category_match.empty:
        category_id = category_match.iloc[0]["id"]

if end_date < start_date:
    st.error("종료일은 시작일보다 늦어야 합니다.")
else:
    if st.button("저장"):
        try:
            if goal_id:
                update_goal(
                    int(goal_id),
                    title=title,
                    start_date=start_date,
                    end_date=end_date,
                    trigger_action=trigger_action,
                    importance=importance,
                    memo=memo,
                    status=status,
                    category_id=category_id,  # 새로 추가
                )
            else:
                add_goal(
                    title,
                    start_date,
                    end_date,
                    trigger_action,
                    importance,
                    memo,
                    status,
                )
            st.success("저장되었습니다!")
            st.query_params.clear()  # experimental 제거
            st.switch_page("pages/1_goal_list.py")
        except Exception as e:
            st.error(f"저장 중 오류가 발생했습니다: {str(e)}")
