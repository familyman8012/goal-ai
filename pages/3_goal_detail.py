import streamlit as st
# 페이지 설정을 최상단으로 이동
st.set_page_config(
    page_title="목표 상세",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",  # "expanded"에서 "collapsed"로 변경
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
from datetime import datetime
from database import get_goals, update_goal, add_goal, get_categories
from config import GOAL_STATUS, IMPORTANCE_LEVELS
import pandas as pd
from utils.auth_utils import login_required, init_auth
from utils.menu_utils import show_menu  # 추가
import pytz



# 메뉴 표시 추가
show_menu()

# 인증 초기화
init_auth()

# 로그인 체크
login_required()

# 전체 목표 데이터 먼저 가져오기
if 'goals_df' not in st.session_state:
    st.session_state.goals_df = get_goals()

# goal_id 가져오는 부분
if 'current_goal_id' not in st.session_state and 'selected_goal_id' in st.session_state:
    st.session_state.current_goal_id = st.session_state.selected_goal_id
    del st.session_state.selected_goal_id

goal_id = st.session_state.get('current_goal_id')

# goal 변수 초기화
goal = None
if goal_id:
    try:
        # id로 목표 찾기
        filtered_goals = st.session_state.goals_df[st.session_state.goals_df["id"].astype(int) == goal_id]
        
        if not filtered_goals.empty:
            goal = filtered_goals.iloc[0]
            st.title(f"목표 상세: {goal['title']}")
        else:
            st.error(f"해당 목표를 찾을 수 없습니다. (ID: {goal_id})")
            if st.button("목록으로 돌아가기"):
                st.session_state.pop('current_goal_id', None)
                st.switch_page("pages/1_goal_list.py")
            st.stop()
    except Exception as e:
        st.error(f"목표 조회 중 오류가 발생했습니다: {str(e)}")
        if st.button("목록으로 돌아가기"):
            st.session_state.pop('current_goal_id', None)
            st.switch_page("pages/1_goal_list.py")
        st.stop()
else:
    st.title("새 목표 추가")

def get_local_datetime(date, time_str):
    """날짜와 시간 문자열을 받아 한국 시간대의 datetime 객체를 반환"""
    try:
        # 시간 문자열 파싱
        time_obj = datetime.strptime(time_str, "%H:%M").time()
        # 날짜와 시간 결합
        dt = datetime.combine(date, time_obj)
        # 한국 시간대 적용
        kst = pytz.timezone('Asia/Seoul')
        return kst.localize(dt)
    except ValueError:
        st.error("올바른 시간 형식을 입력해주세요 (예: 14:30)")
        return None

def format_datetime_for_display(dt):
    """datetime 객체를 표시용 문자열로 변환"""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        kst = pytz.timezone('Asia/Seoul')
        dt = kst.localize(dt)
    return dt.strftime("%H:%M")

# 입력 필드
title = st.text_input("목표", value=goal["title"] if goal is not None else "")

col1, col2 = st.columns(2)

with col1:
    default_start = datetime.now(pytz.timezone('Asia/Seoul'))
    start_date = st.date_input(
        "시작일",
        value=(
            pd.to_datetime(goal["start_date"]).date()
            if goal is not None and pd.notnull(goal["start_date"])
            else default_start.date()
        ),
    )
    
    start_time_str = st.text_input(
        "시작 시간",
        value=(
            format_datetime_for_display(pd.to_datetime(goal["start_date"]))
            if goal is not None and pd.notnull(goal["start_date"])
            else default_start.strftime("%H:%M")
        ),
        help="24시간 형식으로 입력해주세요 (예: 14:30)"
    )

with col2:
    default_end = datetime.now(pytz.timezone('Asia/Seoul'))
    end_date = st.date_input(
        "종료일",
        value=(
            pd.to_datetime(goal["end_date"]).date()
            if goal is not None and pd.notnull(goal["end_date"])
            else default_end.date()
        ),
    )
    
    end_time_str = st.text_input(
        "종료 시간",
        value=(
            format_datetime_for_display(pd.to_datetime(goal["end_date"]))
            if goal is not None and pd.notnull(goal["end_date"])
            else default_end.strftime("%H:%M")
        ),
        help="24시간 형식으로 입력해주세요 (예: 14:30)"
    )

trigger_action = st.text_input(
    "트리거(원인과 결과)", 
    value=goal["trigger_action"] if goal is not None and pd.notnull(goal["trigger_action"]) else ""
)

importance = st.selectbox(
    "중요도",
    IMPORTANCE_LEVELS,
    index=(
        IMPORTANCE_LEVELS.index(goal["importance"])
        if goal is not None and pd.notnull(goal["importance"]) and goal["importance"] in IMPORTANCE_LEVELS
        else 4
    ),
)

memo = st.text_area(
    "메모", 
    value=goal["memo"] if goal is not None and pd.notnull(goal["memo"]) else ""
)

status = st.selectbox(
    "상태",
    GOAL_STATUS,
    index=(
        GOAL_STATUS.index(goal["status"])
        if goal is not None and pd.notnull(goal["status"]) and goal["status"] in GOAL_STATUS
        else 0
    ),
)

# 카테고리 선택
categories_df = get_categories()
category_options = ["전체"] + categories_df["name"].tolist()

# 현재 선택된 카테고리 찾기
current_category_index = 0
if goal is not None and pd.notnull(goal["category_id"]):
    category_match = categories_df[categories_df["id"] == goal["category_id"]]
    if not category_match.empty:
        category_name = category_match.iloc[0]["name"]
        if category_name in category_options:
            current_category_index = category_options.index(category_name)

selected_category = st.selectbox(
    "카테고리",
    category_options,
    index=current_category_index
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
            # 시작 시간과 종료 시간 생성
            start_datetime = get_local_datetime(start_date, start_time_str)
            end_datetime = get_local_datetime(end_date, end_time_str)
            
            if start_datetime is None or end_datetime is None:
                st.error("올바른 시간 형식을 입력해주세요.")
            elif end_datetime < start_datetime:
                st.error("종료일시는 시작일시보다 늦어야 합니다.")
            else:
                if goal_id:
                    update_goal(
                        int(goal_id),
                        title=title,
                        start_date=start_datetime,
                        end_date=end_datetime,
                        trigger_action=trigger_action,
                        importance=importance,
                        memo=memo,
                        status=status,
                        category_id=category_id,
                    )
                else:
                    add_goal(
                        title,
                        start_datetime,
                        end_datetime,
                        trigger_action,
                        importance,
                        memo,
                        status,
                        category_id,
                    )
                st.success("저장되었습니다!")
                st.session_state.pop('current_goal_id', None)
                st.session_state.pop('goals_df', None)
                st.query_params.clear()
                st.switch_page("pages/1_goal_list.py")
        except Exception as e:
            st.error(f"저장 중 오류가 발생했습니다: {str(e)}")
