import streamlit as st
from utils.board_components import render_post_list, render_post_detail, render_post_form

# URL 파라미터 처리
mode = st.query_params.get("mode", "list")
post_id = st.query_params.get("post_id")

if mode == "list":
    render_post_list("info", "정보 게시판")
elif mode == "write":
    render_post_form("info")
elif mode == "view" and post_id:
    render_post_detail(int(post_id), "info")
elif mode == "edit" and post_id:
    render_post_form("info", int(post_id))
