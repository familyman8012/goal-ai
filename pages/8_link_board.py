import streamlit as st
from database import get_links, add_link, update_link, delete_link, get_link
from utils.session_utils import clear_goal_session
import pandas as pd
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



st.title("링크 게시판")

# 새 링크 추가 섹션
with st.expander("➕ 새 링크 추가", expanded=False):
    with st.form("new_link_form"):
        site_name = st.text_input("사이트명")
        url = st.text_input("URL")
        submitted = st.form_submit_button("추가")
        if submitted and site_name and url:
            try:
                add_link(site_name, url)
                st.success("링크가 추가되었습니다!")
                st.rerun()
            except Exception as e:
                st.error(f"링크 추가 중 오류가 발생했습니다: {str(e)}")

# 링크 목록 표시
links_df = get_links()
if links_df.empty:
    st.info("등록된 링크가 없습니다.")
else:
    # 생성일 기준으로 오름차순 정렬
    links_df = links_df.sort_values(by='created_at', ascending=True)
    
    for idx, link in links_df.iterrows():
        col1, col2, col3 = st.columns([6, 1, 1])
        
        # 수정 모드 상태 관리
        edit_mode_key = f"edit_mode_{link['id']}"
        if edit_mode_key not in st.session_state:
            st.session_state[edit_mode_key] = False
        
        with col1:
            if st.session_state[edit_mode_key]:
                # 수정 모드
                new_site_name = st.text_input("사이트명", value=link['site_name'], key=f"site_name_{link['id']}")
                new_url = st.text_input("URL", value=link['url'], key=f"url_{link['id']}")
                if st.button("저장", key=f"save_{link['id']}"):
                    try:
                        update_link(link['id'], new_site_name, new_url)
                        st.session_state[edit_mode_key] = False
                        st.success("링크가 수정되었습니다!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"링크 수정 중 오류가 발생했습니다: {str(e)}")
            else:
                # 표시 모드
                st.markdown(f"[{link['site_name']}]({link['url']})")
        
        with col2:
            if st.button("✏️", key=f"edit_{link['id']}"):
                st.session_state[edit_mode_key] = not st.session_state[edit_mode_key]
                st.rerun()
        
        with col3:
            if st.button("🗑️", key=f"delete_{link['id']}"):
                if delete_link(link['id']):
                    st.success("링크가 삭제되었습니다!")
                    st.rerun()
                else:
                    st.error("링크 삭제 중 오류가 발생했습니다.")
