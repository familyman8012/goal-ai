import streamlit as st

def show_menu():
    # 메뉴 아이템 정의
    menu_items = {
        "목표 목록": "pages/1_goal_list.py",
        "미달성 목표 분석": "pages/2_incomplete_goals_analysis.py",
        "목표 상세": "pages/3_goal_detail.py",
        "카테고리 관리": "pages/4_category_management.py",
        "정보 게시판": "pages/5_info_board.py",
        "아이디어 게시판": "pages/6_idea_board.py",
        "링크 게시판": "pages/8_link_board.py",
        "사용자 가이드": "pages/7_guide.py",
        "프로필 관리": "pages/9_user_profile.py"
    }
    
    # 메뉴 렌더링
    for label, page in menu_items.items():
        if st.sidebar.button(label):
            # 목표 관련 세션 상태 정리
            st.session_state.pop('current_goal_id', None)
            st.session_state.pop('goals_df', None)
            st.switch_page(page)
