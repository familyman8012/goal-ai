import streamlit as st
from database import update_user_profile, get_user_profile
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



st.title("프로필 관리")

# 현재 프로필 정보 가져오기
current_profile = get_user_profile()

# 프로필 입력 폼
with st.form("profile_form"):
    content = st.text_area(
        "프로필 정보",
        value=current_profile.get('content', ''),
        height=200,
        help="""예시:
사용자 정보:
- 45살의 남성
- 프론트엔드개발자
- 현재 연봉 7100만원
- 목표 연봉 8500만원 이상
- 결혼 상태: 미혼
- 건강 관련 주의사항: 혈당이 높음"""
    )
    
    consultant_style = st.text_area(
        "AI 컨설턴트 스타일 설정",
        value=current_profile.get('consultant_style', ''),
        height=100,
        help="AI 컨설턴트가 어떤 스타일로 대화하기를 원하는지 설정하세요."
    )
    
    if st.form_submit_button("저장"):
        try:
            # 프로필 업데이트
            profile_data = {
                'content': content,
                'consultant_style': consultant_style
            }
            
            update_user_profile(profile_data)
            st.success("프로필이 업���이트되었습니다!")
            
        except Exception as e:
            st.error(f"프로필 업데이트 중 오류가 발생했습니다: {str(e)}")

# 프로필 미리보기
if content:
    with st.expander("프로필 미리보기", expanded=True):
        st.markdown(content)
        if consultant_style:
            st.markdown("---")
            st.markdown("**AI 컨설턴트 스타일:**")
            st.markdown(consultant_style)
