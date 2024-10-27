import streamlit as st

st.set_page_config(
    page_title="링크 게시판",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items=None
)

from database import get_links, add_link, update_link, delete_link, get_link
from utils.session_utils import clear_goal_session
import pandas as pd
from utils.auth_utils import login_required, init_auth

# 나머지 코드는 동일...
