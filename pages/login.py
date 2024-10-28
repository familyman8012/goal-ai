import streamlit as st

# 페이지 설정을 최상단으로 이동
st.set_page_config(
    page_title="로그인",
    page_icon="🔐",
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

from utils.auth_utils import login, init_auth
from database import create_user, get_user_by_email, create_initial_profile
from utils.auth_utils import hash_password

# 인증 초기화
init_auth()

# 이미 로그인된 경우 홈으로 리다이렉트
if st.session_state.get('authenticated', False) and st.session_state.get('user_id'):
    st.switch_page("Home.py")
    st.stop()  # 페이지 실행 중단

st.title("로그인")

# 탭 생성
tab1, tab2 = st.tabs(["로그인", "회원가입"])

# 로그인 탭
with tab1:
    with st.form("login_form"):
        email = st.text_input("이메일")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인")
        
        if submitted:
            if login(email, password):
                st.success("로그인 성공!")
                st.switch_page("Home.py")
            else:
                st.error("이메일 또는 비밀번호가 올바르지 않습니다.")

# 회원가입 탭
with tab2:
    with st.form("register_form"):
        new_email = st.text_input("이메일")
        new_username = st.text_input("사용자명 (선택)")
        new_password = st.text_input("비밀번호", type="password")
        confirm_password = st.text_input("비밀번호 확인", type="password")
        submitted = st.form_submit_button("회원가입")
        
        if submitted:
            if not all([new_email, new_password, confirm_password]):
                st.error("이메일과 비밀번호는 필수 입력 항목입니다.")
            elif new_password != confirm_password:
                st.error("비밀번호가 일치하지 않습니다.")
            elif get_user_by_email(new_email):
                st.error("이미 등록된 이메일입니다.")
            else:
                if not new_username:  # 사용자명이 입력되지 않은 경우
                    new_username = new_email.split('@')[0]  # 이메일 주소에서 사용자명 추출
                
                hashed_password = hash_password(new_password)
                user_id = create_user(new_username, new_email, hashed_password)
                if user_id:
                    create_initial_profile(user_id)
                    st.success("회원가입이 완료되었습니다!")
                    st.info("계정 활성화를 위해 관리자에게 문의해주세요.")
                else:
                    st.error("회원가입 중 오류가 발생했습니다.")
