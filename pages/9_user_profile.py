import streamlit as st

st.set_page_config(
    page_title="프로필 관리",
    page_icon="👤",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items=None
)

from database import update_user_profile, get_user_profile
from utils.session_utils import clear_goal_session
from utils.auth_utils import login_required, init_auth

# 나머지 코드는 동일...
