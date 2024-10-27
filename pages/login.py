import streamlit as st

# 페이지 설정을 최상단으로 이동
st.set_page_config(
    page_title="로그인",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items=None
)

from utils.auth_utils import login, init_auth
from database import create_user, get_user_by_username, create_initial_profile
from utils.auth_utils import hash_password

# 인증 초기화
init_auth()

# 이미 로그인된 경우 홈으로 리다이렉트
if st.session_state.get('authenticated', False):
    st.switch_page("Home.py")

st.title("로그인")

# 탭 생성
tab1, tab2 = st.tabs(["로그인", "회원가입"])

with tab1:
    with st.form("login_form"):
        username = st.text_input("사용자명")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인")
        
        if submitted:
            if login(username, password):
                st.success("로그인 성공!")
                st.switch_page("Home.py")
            else:
                st.error("사용자명 또는 비밀번호가 올바르지 않습니다.")

with tab2:
    with st.form("register_form"):
        new_username = st.text_input("사용자명")
        new_email = st.text_input("이메일")
        new_password = st.text_input("비밀번호", type="password")
        confirm_password = st.text_input("비밀번호 확인", type="password")
        submitted = st.form_submit_button("회원가입")
        
        if submitted:
            if not all([new_username, new_email, new_password, confirm_password]):
                st.error("모든 필드를 입력해주세요.")
            elif new_password != confirm_password:
                st.error("비밀번호가 일치하지 않습니다.")
            elif get_user_by_username(new_username):
                st.error("이미 존재하는 사용자명입니다.")
            else:
                hashed_password = hash_password(new_password)
                user_id = create_user(new_username, new_email, hashed_password)
                if user_id:
                    # 초기 프로필 생성
                    create_initial_profile(user_id)
                    st.success("회원가입이 완료되었습니다!")
                    # 자동 로그인
                    if login(new_username, new_password):
                        st.success("자동으로 로그인되었습니다.")
                        st.switch_page("Home.py")
                else:
                    st.error("회원가입 중 오류가 발생했습니다.")
