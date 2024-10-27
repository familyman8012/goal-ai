import streamlit as st
import bcrypt
from functools import wraps
from database import get_user_by_credentials, update_last_login, get_user_by_id, update_session, delete_session
from datetime import datetime, timedelta
import secrets
from streamlit_cookies_controller import CookieController

# 전역 쿠키 컨트롤러 인스턴스 생성
cookie_manager = CookieController()

def hash_password(password: str) -> str:
    """비밀번호 해싱"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_session_token():
    """새로운 세션 토큰 생성"""
    return secrets.token_urlsafe(32)

def login(username: str, password: str) -> bool:
    """로그인 처리"""
    user = get_user_by_credentials(username)
    if user and verify_password(password, user['password_hash']):
        # 세션 토큰 생성
        token = create_session_token()
        expires_at = datetime.now() + timedelta(days=7)
        
        # DB에 세션 정보 저장
        update_session(user['id'], token, expires_at)
        
        # 세션 상태 업데이트
        st.session_state.authenticated = True
        st.session_state.user_id = user['id']
        st.session_state.username = username
        
        # 쿠키에 세션 정보 저장
        cookie_manager.set('session_token', token)
        cookie_manager.set('user_id', str(user['id']))
        
        # 마지막 로그인 시간 업데이트
        update_last_login(user['id'])
        return True
    return False

def logout():
    """로그아웃 처리"""
    if st.session_state.get('session_token'):
        # DB에서 세션 삭제
        delete_session(st.session_state.session_token)
    
    # 쿠키에서 세션 정보 삭제 (max_age=0으로 설정하여 즉시 만료)
    cookie_manager.set('session_token', '', max_age=0)
    cookie_manager.set('user_id', '', max_age=0)
    
    clear_auth_state()

def init_auth():
    """인증 관련 세션 상태 초기화"""
    if 'authenticated' not in st.session_state:
        # 쿠키에서 세션 토큰 확인
        session_token = cookie_manager.get('session_token')
        user_id = cookie_manager.get('user_id')
        
        if session_token and user_id:
            user = get_user_by_id(int(user_id))
            if user:
                st.session_state.authenticated = True
                st.session_state.user_id = user['id']
                st.session_state.username = user['username']
                st.session_state.session_token = session_token
                
                # 세션 연장
                expires_at = datetime.now() + timedelta(days=7)
                update_session(user['id'], session_token, expires_at)
            else:
                clear_auth_state()
                cookie_manager.set('session_token', '', max_age=0)
                cookie_manager.set('user_id', '', max_age=0)
        else:
            clear_auth_state()

def login_required(func=None):
    """로그인 필요한 페이지에 대한 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            init_auth()  # 세션 상태 확인
            if not st.session_state.get('authenticated', False):
                st.warning("로그인이 필요한 페이지입니다.")
                st.switch_page("pages/login.py")
            return func(*args, **kwargs)
        return wrapper
    
    if func is None:
        return decorator
    return decorator(func)

def clear_auth_state():
    """인증 상태 초기화"""
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.session_token = None
