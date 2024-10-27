import streamlit as st

st.set_page_config(
    page_title="아이디어 게시판",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items=None
)

from utils.board_components import render_post_list, render_post_detail, render_post_form
from utils.session_utils import clear_goal_session
from utils.auth_utils import login_required, init_auth
from utils.menu_utils import show_menu  # 추가

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
    render_post_list("idea", "아이디어 게시판")
elif mode == "write":
    render_post_form("idea")
elif mode == "view" and post_id:
    render_post_detail(int(post_id), "idea")
elif mode == "edit" and post_id:
    render_post_form("idea", int(post_id))
