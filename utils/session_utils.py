import streamlit as st

def clear_goal_session():
    """목표 관련 세션 상태를 정리하는 함수"""
    st.session_state.pop('current_goal_id', None)
    st.session_state.pop('goals_df', None)
