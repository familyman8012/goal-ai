import secrets
from datetime import datetime, timedelta
import streamlit as st
from database import update_session

class SessionManager:
    def __init__(self):
        if 'session_data' not in st.session_state:
            st.session_state.session_data = {
                'token': None,
                'user_id': None,
                'username': None,
                'login_time': None,
                'last_activity': None,
                'expires_at': None
            }

    def create_session(self, user_id: int, username: str):
        """새로운 세션 생성"""
        session_token = secrets.token_urlsafe(32)
        now = datetime.now()
        
        # 세션 데이터 설정
        st.session_state.session_data = {
            'token': session_token,
            'user_id': user_id,
            'username': username,
            'login_time': now,
            'last_activity': now,
            'expires_at': now + timedelta(hours=24)  # 24시간 후 만료
        }
        
        # DB에 세션 정보 저장
        update_session(user_id, session_token, now + timedelta(hours=24))
        
        return session_token

    def validate_session(self) -> bool:
        """세션 유효성 검사"""
        if not st.session_state.session_data['token']:
            return False
            
        now = datetime.now()
        
        # 세션 만료 체크
        if now > st.session_state.session_data['expires_at']:
            self.clear_session()
            return False
            
        # 마지막 활동 시간이 30분 이상 지났는지 체크
        if (now - st.session_state.session_data['last_activity']) > timedelta(minutes=30):
            self.clear_session()
            return False
            
        # 활동 시간 업데이트
        st.session_state.session_data['last_activity'] = now
        return True

    def clear_session(self):
        """세션 정리"""
        st.session_state.session_data = {
            'token': None,
            'user_id': None,
            'username': None,
            'login_time': None,
            'last_activity': None,
            'expires_at': None
        }

    def get_user_id(self) -> int:
        """현재 로그인한 사용자 ID 반환"""
        return st.session_state.session_data['user_id']

    def get_username(self) -> str:
        """현재 로그인한 사용자명 반환"""
        return st.session_state.session_data['username']

    def extend_session(self):
        """세션 연장"""
        now = datetime.now()
        st.session_state.session_data['expires_at'] = now + timedelta(hours=24)
        update_session(
            self.get_user_id(), 
            st.session_state.session_data['token'],
            st.session_state.session_data['expires_at']
        )

def clear_goal_session():
    """목표 관련 세션 상태를 정리하는 함수"""
    st.session_state.pop('current_goal_id', None)
    st.session_state.pop('goals_df', None)
