import streamlit as st
from database import get_posts
from utils.menu_utils import show_menu
from utils.auth_utils import login_required, init_auth
from datetime import datetime

# 인증 초기화
init_auth()

# 로그인 체크
if not st.session_state.get(
    "authenticated", False
) or not st.session_state.get("user_id"):
    st.switch_page("pages/login.py")
    st.stop()

# 페이지 설정
st.set_page_config(
    page_title="대화 기록",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="collapsed",
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

# 메뉴 표시
show_menu()

st.title("💬 대화 기록")

# 대화 기록 가져오기 (board_type이 'chat'인 게시물만)
chat_records = get_posts(board_type="chat")

if not chat_records.empty:
    for _, record in chat_records.iterrows():
        with st.expander(
            f"📝 {record['title']} ({record['created_at'].strftime('%Y-%m-%d %H:%M')})"
        ):
            st.markdown(record["content"])
            st.markdown("---")
else:
    st.info("저장된 대화 기록이 없습니다.")
