import streamlit as st
import bcrypt
from functools import wraps
from database import get_user_by_credentials, update_last_login, update_session, delete_session, get_session
from datetime import datetime, timedelta
import secrets

def hash_password(password: str) -> str:
    """비밀번호 해싱"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_session_token(user_id: int):
    """새로운 세션 토큰 생성"""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=7)  # 7일 후 만료
    update_session(user_id, token, expires_at)
    return token, expires_at

def login(username: str, password: str) -> bool:
    """로그인 처리"""
    user = get_user_by_credentials(username)
    if user and verify_password(password, user['password_hash']):
        # 세션 토큰 생성
        token, expires_at = create_session_token(user['id'])
        
        # 세션 상태 업데이트
        st.session_state.authenticated = True
        st.session_state.user_id = user['id']
        st.session_state.username = username
        st.session_state.session_token = token
        
        # localStorage에 세션 토큰 저장 (sessionStorage 대신)
        js_code = f"""
        <script>
            localStorage.setItem('session_token', '{token}');
        </script>
        """
        st.components.v1.html(js_code, height=0)
        
        # 마지막 로그인 시간 업데이트
        update_last_login(user['id'])
        return True
    return False

def logout():
    """로그아웃 처리"""
    if st.session_state.get('session_token'):
        # DB에서 세션 삭제
        delete_session(st.session_state.session_token)
    
    # localStorage에서 세션 토큰 제거
    js_code = """
    <script>
        localStorage.removeItem('session_token');
    </script>
    """
    st.components.v1.html(js_code, height=0)
    
    clear_auth_state()

def init_auth():
    """인증 관련 세션 상태 초기화"""
    if 'authenticated' not in st.session_state:
        # localStorage에서 세션 토큰 가져오기
        js_code = """
        <script>
            const token = localStorage.getItem('session_token');
            if (token) {
                window.parent.postMessage({type: 'session_token', token: token}, '*');
            }
        </script>
        """
        st.components.v1.html(js_code, height=0)
        
        # JavaScript에서 전달받은 토큰으로 세션 검증
        session_token = st.experimental_get_query_params().get('session_token', [None])[0]
        if session_token:
            session = get_session(session_token)
            if session:
                user_id, expires_at = session
                st.session_state.authenticated = True
                st.session_state.user_id = user_id
                st.session_state.session_token = session_token
                
                # 세션 연장
                new_expires_at = datetime.now() + timedelta(days=7)
                update_session(user_id, session_token, new_expires_at)
            else:
                clear_auth_state()
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
