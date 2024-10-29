import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from database import (
    get_goals,
    get_categories,
    delete_goal,
    get_links,
    get_posts,
    update_goal,
)
from utils.auth_utils import login_required, init_auth
from utils.menu_utils import show_menu
import pytz

# 페이지 설정
st.set_page_config(
    page_title="목표 목록",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
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


def format_time(dt):
    """datetime 객체에서 시간을 포맷팅하는 함수"""
    if dt.tzinfo is None:
        # timezone이 없는 경우 KST 적용
        dt = pytz.timezone("Asia/Seoul").localize(dt)
    return dt.strftime("%H:%M")


def show_goals_by_date(selected_date, goals_df):
    """선택된 날짜의 목표들을 표시하는 함수"""
    # 선택된 날짜의 목표��� 필터링
    day_goals = goals_df[
        (pd.to_datetime(goals_df["start_date"]).dt.date <= selected_date)
        & (pd.to_datetime(goals_df["end_date"]).dt.date >= selected_date)
    ]

    if day_goals.empty:
        st.info(
            f"{selected_date.strftime('%Y년 %m월 %d일')}에 해당하는 목표가 없습니다."
        )
    else:
        col1, col2 = st.columns(2)

        # 진행 중인 목표
        with col1:
            st.subheader("진행 중인 목표")
            incomplete_goals = day_goals[day_goals["status"] != "완료"]
            if incomplete_goals.empty:
                st.info("진행 중인 목표가 없습니다.")
            else:
                for idx, goal in incomplete_goals.iterrows():
                    start_datetime = pd.to_datetime(goal["start_date"])
                    end_datetime = pd.to_datetime(goal["end_date"])

                    start_time_str = format_time(start_datetime)
                    end_time_str = format_time(end_datetime)
                    time_str = f"{start_time_str} - {end_time_str}"

                    goal_col1, goal_col2, goal_col3 = st.columns([6, 1, 1])

                    with goal_col1:
                        unique_key = f"date_incomplete_{goal['id']}_{idx}"
                        if st.button(
                            f"📌 {goal['title']} ({time_str})", key=unique_key
                        ):
                            st.session_state.selected_goal_id = int(goal["id"])
                            st.switch_page("pages/3_goal_detail.py")

                    with goal_col2:
                        complete_key = f"complete_date_{goal['id']}_{idx}"
                        if st.button("✅", key=complete_key, help="목표 완료"):
                            update_goal(goal["id"], status="완료")
                            st.success(
                                f"'{goal['title']}' 목표가 완료되었습니다."
                            )
                            st.rerun()

                    with goal_col3:
                        delete_key = f"delete_date_{goal['id']}_{idx}"
                        if st.button("✕", key=delete_key, help="목표 삭제"):
                            if delete_goal(goal["id"]):
                                st.success(
                                    f"'{goal['title']}' 목표가 삭제되었습니다."
                                )
                                st.rerun()
                            else:
                                st.error("목표 삭제 중 오류가 발생했습니다.")

        # 완���된 목표
        with col2:
            st.subheader("완료된 목표")
            complete_goals = day_goals[day_goals["status"] == "완료"]
            if complete_goals.empty:
                st.info("완료된 목표가 없습니다.")
            else:
                for idx, goal in complete_goals.iterrows():
                    start_datetime = pd.to_datetime(goal["start_date"])
                    end_datetime = pd.to_datetime(goal["end_date"])

                    start_time_str = format_time(start_datetime)
                    end_time_str = format_time(end_datetime)
                    time_str = f"{start_time_str} - {end_time_str}"

                    unique_key = f"date_complete_{goal['id']}_{idx}"
                    if st.button(
                        f"✅ {goal['title']} ({time_str})", key=unique_key
                    ):
                        st.session_state.selected_goal_id = int(goal["id"])
                        st.switch_page("pages/3_goal_detail.py")

    # 해당 날짜의 회고 표시
    st.subheader(f"{selected_date.strftime('%Y년 %m월 %d일')}의 회고")
    reflections = get_posts("reflection")
    day_reflection = (
        reflections.query("reflection_date == @selected_date").iloc[0]
        if not reflections.empty
        and not reflections.query("reflection_date == @selected_date").empty
        else None
    )

    if day_reflection is not None:
        col1, col2 = st.columns([6, 1])
        with col1:
            st.markdown(f"### {day_reflection['title']}")
            st.markdown(day_reflection["content"])
        with col2:
            if st.button("✏️", key=f"edit_reflection_{selected_date}"):
                st.query_params["mode"] = "edit"
                st.query_params["post_id"] = str(day_reflection["id"])
                st.switch_page("pages/10_reflection_board.py")
    else:
        col1, col2 = st.columns([6, 1])
        with col1:
            st.info("이 날의 회고가 없습니다.")
        with col2:
            if st.button("✏️ 작성", key=f"write_reflection_{selected_date}"):
                st.query_params["mode"] = "write"
                st.switch_page("pages/10_reflection_board.py")


# 메인 로직
def main():
    # 인증 초기화
    init_auth()

    # 로그인 체크
    login_required()

    # 메뉴 표시
    show_menu()

    # 세션 상태 정리
    st.session_state.pop("current_goal_id", None)
    st.session_state.pop("goals_df", None)

    st.title("진행중/완료 목표 목록")

    # 전체 목표 데이터 가져오기
    goals_df = get_goals()

    if goals_df.empty:
        st.info(
            "등록된 목표가 없습니다. '새 목표 추가'에서 목표를 추가해보세요!"
        )
        return

    # 카테고리 필터
    categories_df = get_categories()
    category_options = ["전체"] + categories_df["name"].tolist()
    selected_category = st.selectbox("카테고리 필터", category_options)

    # 필터링된 데이터프레임 생성
    current_time = pd.Timestamp.now(tz=pytz.timezone("Asia/Seoul"))

    # 각 기간별 필터링된 데이터프레임 생성
    filtered_dfs = {
        "오늘": goals_df[
            (
                pd.to_datetime(goals_df["start_date"]).dt.date
                == current_time.date()
            )
            | (
                pd.to_datetime(goals_df["end_date"]).dt.date
                == current_time.date()
            )
            | (
                (pd.to_datetime(goals_df["start_date"]) <= current_time)
                & (pd.to_datetime(goals_df["end_date"]) >= current_time)
            )
        ],
        "내일": goals_df[
            (
                pd.to_datetime(goals_df["start_date"]).dt.date
                == (current_time + timedelta(days=1)).date()
            )
            | (
                pd.to_datetime(goals_df["end_date"]).dt.date
                == (current_time + timedelta(days=1)).date()
            )
        ],
        "2일 후": goals_df[
            (
                pd.to_datetime(goals_df["start_date"]).dt.date
                == (current_time + timedelta(days=2)).date()
            )
            | (
                pd.to_datetime(goals_df["end_date"]).dt.date
                == (current_time + timedelta(days=2)).date()
            )
        ],
        "3일 후": goals_df[
            (
                pd.to_datetime(goals_df["start_date"]).dt.date
                == (current_time + timedelta(days=3)).date()
            )
            | (
                pd.to_datetime(goals_df["end_date"]).dt.date
                == (current_time + timedelta(days=3)).date()
            )
        ],
        "1주": goals_df[
            (
                pd.to_datetime(goals_df["start_date"]).dt.date
                <= (current_time + timedelta(days=7)).date()
            )
            & (
                pd.to_datetime(goals_df["end_date"]).dt.date
                >= current_time.date()
            )
        ],
        "1개월": goals_df[
            (
                pd.to_datetime(goals_df["start_date"]).dt.date
                <= (current_time + timedelta(days=30)).date()
            )
            & (
                pd.to_datetime(goals_df["end_date"]).dt.date
                >= current_time.date()
            )
        ],
        "1년": goals_df[
            (
                pd.to_datetime(goals_df["start_date"]).dt.date
                <= (current_time + timedelta(days=365)).date()
            )
            & (
                pd.to_datetime(goals_df["end_date"]).dt.date
                >= current_time.date()
            )
        ],
    }

    # 카테고리 필터링
    if selected_category != "전체":
        category_id = categories_df[
            categories_df["name"] == selected_category
        ].iloc[0]["id"]
        filtered_dfs = {
            period: df[df["category_id"] == category_id]
            for period, df in filtered_dfs.items()
        }

    # 탭 생성 및 표시
    tabs = st.tabs(
        ["오늘", "내일", "2일 후", "3일 후", "1주", "1개월", "1년", "전체"]
    )

    # 각 탭의 내용 표시
    for tab, (period, filtered_df) in zip(tabs[:-1], filtered_dfs.items()):
        with tab:
            if filtered_df.empty:
                st.info(f"{period}의 목표가 없습니다.")
            else:
                col1, col2 = st.columns(2)

                # 진행 중인 목표
                with col1:
                    st.subheader("진행 중인 목표")
                    incomplete_goals = filtered_df[
                        filtered_df["status"] != "완료"
                    ]
                    if incomplete_goals.empty:
                        st.info("진행 중인 목표가 없습니다.")
                    else:
                        for idx, goal in incomplete_goals.iterrows():
                            start_datetime = pd.to_datetime(goal["start_date"])
                            end_datetime = pd.to_datetime(goal["end_date"])

                            start_time_str = format_time(start_datetime)
                            end_time_str = format_time(end_datetime)
                            time_str = f"{start_time_str} - {end_time_str}"

                            goal_col1, goal_col2, goal_col3 = st.columns(
                                [6, 1, 1]
                            )

                            with goal_col1:
                                unique_key = (
                                    f"{period}_incomplete_{goal['id']}_{idx}"
                                )
                                if st.button(
                                    f"📌 {goal['title']} ({time_str})",
                                    key=unique_key,
                                ):
                                    st.session_state.selected_goal_id = int(
                                        goal["id"]
                                    )
                                    st.switch_page("pages/3_goal_detail.py")

                            with goal_col2:
                                complete_key = (
                                    f"complete_{period}_{goal['id']}_{idx}"
                                )
                                if st.button(
                                    "✅", key=complete_key, help="목표 완료"
                                ):
                                    update_goal(goal["id"], status="완료")
                                    st.success(
                                        f"'{goal['title']}' 목표가 완료되었습니다."
                                    )
                                    st.rerun()

                            with goal_col3:
                                delete_key = (
                                    f"delete_{period}_{goal['id']}_{idx}"
                                )
                                if st.button(
                                    "✕", key=delete_key, help="목표 삭제"
                                ):
                                    if delete_goal(goal["id"]):
                                        st.success(
                                            f"'{goal['title']}' 목표가 삭제되었습니다."
                                        )
                                        st.rerun()
                                    else:
                                        st.error(
                                            "목표 삭제 중 오류가 발생했습니다."
                                        )

                # 완료된 목표
                with col2:
                    st.subheader("완료된 목표")
                    complete_goals = filtered_df[
                        filtered_df["status"] == "완료"
                    ]
                    if complete_goals.empty:
                        st.info("완료된 목표가 없습니다.")
                    else:
                        for idx, goal in complete_goals.iterrows():
                            start_datetime = pd.to_datetime(goal["start_date"])
                            end_datetime = pd.to_datetime(goal["end_date"])

                            start_time_str = format_time(start_datetime)
                            end_time_str = format_time(end_datetime)
                            time_str = f"{start_time_str} - {end_time_str}"

                            unique_key = (
                                f"{period}_complete_{goal['id']}_{idx}"
                            )
                            if st.button(
                                f"✅ {goal['title']} ({time_str})",
                                key=unique_key,
                            ):
                                st.session_state.selected_goal_id = int(
                                    goal["id"]
                                )
                                st.switch_page("pages/3_goal_detail.py")

                # 오늘 탭에만 회고 섹션 추가
                if period == "오늘":
                    st.subheader(f"오늘의 회고")
                    reflections = get_posts("reflection")
                    today_reflection = (
                        reflections.query(
                            "reflection_date == @current_time.date()"
                        ).iloc[0]
                        if not reflections.empty
                        and not reflections.query(
                            "reflection_date == @current_time.date()"
                        ).empty
                        else None
                    )

                    if today_reflection is not None:
                        col1, col2 = st.columns([6, 1])
                        with col1:
                            st.markdown(f"### {today_reflection['title']}")
                            st.markdown(today_reflection["content"])
                        with col2:
                            if st.button("✏️", key=f"edit_reflection_today"):
                                st.query_params["mode"] = "edit"
                                st.query_params["post_id"] = str(
                                    today_reflection["id"]
                                )
                                st.switch_page("pages/10_reflection_board.py")
                    else:
                        col1, col2 = st.columns([6, 1])
                        with col1:
                            st.info("오늘의 회고가 없습니다.")
                        with col2:
                            if st.button(
                                "✏️ 작성", key=f"write_reflection_today"
                            ):
                                st.query_params["mode"] = "write"
                                st.switch_page("pages/10_reflection_board.py")

    # 전체 탭
    with tabs[-1]:
        st.subheader("날짜별 목표 보기")
        selected_date = st.date_input(
            "날짜 선택",
            value=datetime.now(pytz.timezone("Asia/Seoul")).date(),
            help="목표를 확인할 날짜를 선택하세요",
        )
        show_goals_by_date(selected_date, goals_df)


if __name__ == "__main__":
    main()
