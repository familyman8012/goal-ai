import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from database import get_goals, get_categories, delete_goal, get_links  # get_links 추가

# 시간 포맷팅 함수 추가 - 파일 상단으로 이동
def format_time(dt):
    """datetime을 '오전/오후 시:분' 형식으로 변환"""
    if pd.isnull(dt):
        return ""
    dt = pd.to_datetime(dt)
    hour = dt.hour
    if hour == 0:
        return f"오전 12:{dt.strftime('%M')}"
    elif hour < 12:
        return f"오전 {hour}:{dt.strftime('%M')}"
    elif hour == 12:
        return f"오후 12:{dt.strftime('%M')}"
    else:
        return f"오후 {hour-12}:{dt.strftime('%M')}"

st.set_page_config(
    page_title="목표 목록",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items=None
)

# 페이지 진입 시 목표 관련 세션 상태 정리
st.session_state.pop('current_goal_id', None)
st.session_state.pop('goals_df', None)

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
        "오늘": goals_df[
            # 오늘 시작하는 목표
            (
                (
                    pd.to_datetime(goals_df["start_date"]).dt.date
                    == current_time.date()
                )
            )
            |
            # 오늘 끝하는 목표
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
        "내일": goals_df[
            (
                pd.to_datetime(goals_df["start_date"]).dt.date
                == (current_time + timedelta(days=1)).date()
            )
            |
            (
                pd.to_datetime(goals_df["end_date"]).dt.date
                == (current_time + timedelta(days=1)).date()
            )
        ],
        "2일 후": goals_df[
            (
                pd.to_datetime(goals_df["start_date"]).dt.date
                == (current_time + timedelta(days=2)).date()
            )
            |
            (
                pd.to_datetime(goals_df["end_date"]).dt.date
                == (current_time + timedelta(days=2)).date()
            )
        ],
        "3일 후": goals_df[
            (
                pd.to_datetime(goals_df["start_date"]).dt.date
                == (current_time + timedelta(days=3)).date()
            )
            |
            (
                pd.to_datetime(goals_df["end_date"]).dt.date
                == (current_time + timedelta(days=3)).date()
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
        "전체": goals_df,
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
            # 진행 중인 목표와 완료된 목표, 미완료된 목표를 나란히 표시하기 위한 컬럼 생성
            if period == "오늘":
                # 진행 중인 목표와 완료된 목표를 나란히 표시
                col1, col2 = st.columns(2)
                
                # 진행 중인 목표
                with col1:
                    st.subheader("진행 중인 목표")
                    incomplete_goals = filtered_df[filtered_df["status"] != "완료"]
                    if incomplete_goals.empty:
                        st.info("진행 중인 목표가 없습니다.")
                    else:
                        for idx, goal in incomplete_goals.iterrows():
                            start_datetime = pd.to_datetime(goal["start_date"])
                            end_datetime = pd.to_datetime(goal["end_date"])
                            
                            # 날짜와 시간 포맷팅
                            date_str = start_datetime.strftime("%Y-%m-%d")
                            start_time_str = format_time(start_datetime)
                            end_time_str = format_time(end_datetime)
                            time_str = f"{start_time_str} - {end_time_str}"

                            # 목표 제목과 삭제 버튼을 나란히 배치하기 위한 컬럼 생성
                            goal_col1, goal_col2 = st.columns([6, 1])

                            with goal_col1:
                                unique_key = f"incomplete_{goal['id']}_{period}_{idx}"
                                if st.button(f"📌 {goal['title']} ({date_str} {time_str})", key=unique_key):
                                    try:
                                        goal_id = int(goal['id'])
                                        st.session_state.selected_goal_id = goal_id
                                        st.switch_page("pages/3_goal_detail.py")
                                    except Exception as e:
                                        st.error(f"Error processing goal ID: {str(e)}")

                            with goal_col2:
                                delete_key = f"delete_{goal['id']}_{period}_{idx}"
                                if st.button("✕", key=delete_key):
                                    if delete_goal(goal["id"]):
                                        st.success(f"'{goal['title']}' 목표가 삭제되었습니다.")
                                        st.rerun()
                                    else:
                                        st.error("목표 삭제 중 오류가 발생했습니다.")

                # 완료된 목표
                with col2:
                    st.subheader("완료된 목표")
                    complete_goals = filtered_df[filtered_df["status"] == "완료"]
                    if complete_goals.empty:
                        st.info("완료된 목표가 없습니다.")
                    else:
                        for idx, goal in complete_goals.iterrows():
                            start_datetime = pd.to_datetime(goal["start_date"])
                            end_datetime = pd.to_datetime(goal["end_date"])
                            
                            # 날짜와 시간 포맷팅
                            date_str = start_datetime.strftime("%Y-%m-%d")
                            start_time_str = format_time(start_datetime)
                            end_time_str = format_time(end_datetime)
                            time_str = f"{start_time_str} - {end_time_str}"

                            unique_key = f"complete_{goal['id']}_{period}_{idx}"
                            if st.button(f"✅ {goal['title']} ({date_str} {time_str})", key=unique_key):
                                try:
                                    goal_id = int(goal['id'])
                                    st.session_state.selected_goal_id = goal_id
                                    st.switch_page("pages/3_goal_detail.py")
                                except Exception as e:
                                    st.error(f"Error processing goal ID: {str(e)}")

                # 미완료된 목표 (오늘 이전) - 전체 너비로 표시
                st.subheader("미완료된 목표")
                # 오늘 이전의 미완료 목표 필터링
                overdue_goals = goals_df[
                    (pd.to_datetime(goals_df["end_date"]) < pd.Timestamp(current_time.date())) &
                    (goals_df["status"] != "완료")
                ]
                if overdue_goals.empty:
                    st.info("미완료된 목표가 없습니다.")
                else:
                    for idx, goal in overdue_goals.iterrows():
                        start_datetime = pd.to_datetime(goal["start_date"])
                        end_datetime = pd.to_datetime(goal["end_date"])
                        
                        # 날짜와 시간 포맷팅
                        date_str = start_datetime.strftime("%Y-%m-%d")
                        start_time_str = format_time(start_datetime)
                        end_time_str = format_time(end_datetime)
                        time_str = f"{start_time_str} - {end_time_str}"

                        # 목표 제목과 삭제 버튼을 나란히 배치하기 위한 컬럼 생성
                        goal_col1, goal_col2 = st.columns([6, 1])

                        with goal_col1:
                            unique_key = f"overdue_{goal['id']}_{period}_{idx}"
                            if st.button(f"⚠️ {goal['title']} ({date_str} {time_str})", key=unique_key):
                                try:
                                    goal_id = int(goal['id'])
                                    st.session_state.selected_goal_id = goal_id
                                    st.switch_page("pages/3_goal_detail.py")
                                except Exception as e:
                                    st.error(f"Error processing goal ID: {str(e)}")

                        with goal_col2:
                            delete_key = f"delete_overdue_{goal['id']}_{period}_{idx}"
                            if st.button("✕", key=delete_key):
                                if delete_goal(goal["id"]):
                                    st.success(f"'{goal['title']}' 목표가 삭제되었습니다.")
                                    st.rerun()
                                else:
                                    st.error("목표 삭제 중 오류가 발생했습니다.")
            else:
                # 다른 탭들은 기존 2컬럼 레이아웃 유지
                col1, col2 = st.columns(2)
                
                # 진행 중인 목표
                with col1:
                    st.subheader("진행 중인 목표")
                    incomplete_goals = filtered_df[filtered_df["status"] != "완료"]
                    if incomplete_goals.empty:
                        st.info("진행 중인 목표가 없습니다.")
                    else:
                        for idx, goal in incomplete_goals.iterrows():
                            start_datetime = pd.to_datetime(goal["start_date"])
                            end_datetime = pd.to_datetime(goal["end_date"])
                            
                            # 날짜와 시간 포맷팅
                            date_str = start_datetime.strftime("%Y-%m-%d")
                            start_time_str = format_time(start_datetime)
                            end_time_str = format_time(end_datetime)
                            time_str = f"{start_time_str} - {end_time_str}"

                            # 목표 제목과 삭제 버튼을 나란히 배치하기 위한 컬럼 생성
                            goal_col1, goal_col2 = st.columns([6, 1])

                            with goal_col1:
                                unique_key = f"incomplete_{goal['id']}_{period}_{idx}"
                                if st.button(f"📌 {goal['title']} ({date_str} {time_str})", key=unique_key):
                                    try:
                                        goal_id = int(goal['id'])
                                        st.session_state.selected_goal_id = goal_id
                                        st.switch_page("pages/3_goal_detail.py")
                                    except Exception as e:
                                        st.error(f"Error processing goal ID: {str(e)}")

                            with goal_col2:
                                delete_key = f"delete_{goal['id']}_{period}_{idx}"
                                if st.button("✕", key=delete_key):
                                    if delete_goal(goal["id"]):
                                        st.success(f"'{goal['title']}' 목표가 삭제되었습니다.")
                                        st.rerun()
                                    else:
                                        st.error("목표 삭제 중 오류가 발생했습니다.")

                # 완료된 목표
                with col2:
                    st.subheader("완료된 목표")
                    complete_goals = filtered_df[filtered_df["status"] == "완료"]
                    if complete_goals.empty:
                        st.info("완료된 목표가 없습니다.")
                    else:
                        for idx, goal in complete_goals.iterrows():
                            start_datetime = pd.to_datetime(goal["start_date"])
                            end_datetime = pd.to_datetime(goal["end_date"])
                            
                            # 날짜와 시간 포맷팅
                            date_str = start_datetime.strftime("%Y-%m-%d")
                            start_time_str = format_time(start_datetime)
                            end_time_str = format_time(end_datetime)
                            time_str = f"{start_time_str} - {end_time_str}"

                            unique_key = f"complete_{goal['id']}_{period}_{idx}"
                            if st.button(f"✅ {goal['title']} ({date_str} {time_str})", key=unique_key):
                                try:
                                    goal_id = int(goal['id'])
                                    st.session_state.selected_goal_id = goal_id
                                    st.switch_page("pages/3_goal_detail.py")
                                except Exception as e:
                                    st.error(f"Error processing goal ID: {str(e)}")

    # filtered_dfs 정의 후에 시간순 정렬 수정
    for period in filtered_dfs:
        filtered_dfs[period] = filtered_dfs[period].sort_values(by='start_date', ascending=False)

# 링크 목록 표시
links_df = get_links()
if links_df.empty:
    st.info("등록된 링크가 없습니다.")
else:
    # 시간순으로 정렬
    for period in filtered_dfs:
        filtered_dfs[period] = filtered_dfs[period].sort_values(by='start_date')

