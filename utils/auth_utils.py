import streamlit as st
from database import get_user_by_credentials, create_user, update_last_login
import bcrypt
from datetime import datetime

def hash_password(password: str) -> str:
    """비밀번호를 해시화하는 함수"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """비밀번호를 검증하는 함수"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def login_required():
    """로그인이 필요한 페이지에서 사용하는 데코레이터"""
    if 'user_id' not in st.session_state:
        st.warning("로그인이 필요한 페이지입니다.")
        st.switch_page("pages/login.py")
        st.stop()

def init_auth():
    """인증 관련 세션 상태 초기화"""
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = None

def login(username: str, password: str) -> bool:
    """로그인 처리 함수"""
    user = get_user_by_credentials(username)
    if user and verify_password(password, user['password_hash']):
        st.session_state.user_id = user['id']
        st.session_state.username = user['username']
        update_last_login(user['id'])
        return True
    return False

def logout():
    """로그아웃 처리 함수"""
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.clear()
