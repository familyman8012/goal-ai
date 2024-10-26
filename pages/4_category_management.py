import streamlit as st
from database import (
    get_categories,
    add_category,
    update_category,
    delete_category,
)
from utils.session_utils import clear_goal_session

# 페이지 진입 시 세션 정리
clear_goal_session()

st.set_page_config(
    page_title="카테고리 관리",
    page_icon="📁",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items=None
)

# 나머지 코드는 동일...

st.title("카테고리 관리")

# 새 카테고리 추가
with st.form("new_category"):
    new_category = st.text_input("새 카테고리 이름")
    submitted = st.form_submit_button("추가")
    if submitted and new_category:
        try:
            add_category(new_category)
            st.success(f"카테고리 '{new_category}'가 추가되었습니다!")
            st.rerun()
        except Exception as e:
            st.error(f"카테고리 추가 중 오류가 발생했습니다: {str(e)}")

# 카테고리 목록 표시
categories_df = get_categories()
if not categories_df.empty:
    st.subheader("카테고리 목록")
    for idx, category in categories_df.iterrows():
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.text(category["name"])
        with col2:
            if st.button("수정", key=f"edit_{category['id']}"):
                st.session_state[f"edit_mode_{category['id']}"] = True
        with col3:
            if st.button("삭제", key=f"delete_{category['id']}"):
                delete_category(category["id"])
                st.success(f"카테고리 '{category['name']}'가 삭제되었습니다!")
                st.rerun()

        # 수정 모드
        if st.session_state.get(f"edit_mode_{category['id']}", False):
            with st.form(f"edit_category_{category['id']}"):
                new_name = st.text_input("새 이름", value=category["name"])
                if st.form_submit_button("저장"):
                    update_category(category["id"], new_name)
                    st.success("카테고리가 수정되었습니다!")
                    st.session_state[f"edit_mode_{category['id']}"] = False
                    st.rerun()
else:
    st.info("등록된 카테고리가 없습니다.")
