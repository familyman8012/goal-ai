import streamlit as st

st.set_page_config(
    page_title="정보 게시판",
    page_icon="📢",
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

from utils.board_components import render_post_list, render_post_detail, render_post_form
from utils.session_utils import clear_goal_session
from utils.auth_utils import login_required, init_auth
from utils.menu_utils import show_menu

# 인증 초기화
init_auth()

# 로그인 체크
login_required()

# 페이지 진입 시 세션 정리
clear_goal_session()

# 메뉴 표시 추가
show_menu()

# URL 파라미터 처리
mode = st.query_params.get("mode", "list")
post_id = st.query_params.get("post_id")

if mode == "list":
    render_post_list("info", "정보 게시판")
elif mode == "write":
    render_post_form("info")
elif mode == "view" and post_id:
    render_post_detail(int(post_id), "info")
elif mode == "edit" and post_id:
    render_post_form("info", int(post_id))
