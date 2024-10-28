import streamlit as st
from database import add_post, get_posts, get_post, update_post, delete_post
from datetime import datetime
import os
from PIL import Image
import uuid
import pandas as pd
import pytz

# 이미지 저장 경로 설정
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def save_uploaded_image(uploaded_file):
    """업로드된 이미지를 저장하고 경로를 반환하는 함수"""
    if uploaded_file is None:
        return None
        
    # 고유한 파일명 생성
    file_ext = os.path.splitext(uploaded_file.name)[1]
    file_name = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    
    # 이미지 저장
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    return file_path

def render_post_list(board_type: str, board_title: str):
    """게시글 목록을 렌더링하는 함수"""
    st.title(board_title)
    
    # 새 글 작성 버튼
    if st.button("✏️ 새 글 작성"):
        st.query_params["mode"] = "write"
        st.rerun()
        
    # 게시글 목록 표시
    posts = get_posts(board_type)
    if posts.empty:
        st.info("등록된 글이 없습니다.")
    else:
        for idx, post in posts.iterrows():
            # 수정일이 있으면 수정일을, 없으면 작성일을 표시
            display_date = post['updated_at'].strftime("%Y-%m-%d") if post['updated_at'] else post['created_at'].strftime("%Y-%m-%d")
            
            # 버튼 하에 제목과 날짜를 함께 표시
            if st.button(f"📄 {post['title']} ({display_date})", key=f"post_{post['id']}"):
                st.query_params["post_id"] = str(post['id'])
                st.query_params["mode"] = "view"
                st.rerun()

def render_post_detail(post_id: int, board_type: str):
    """게시글 상세 보기를 렌더링하는 함수"""
    post = get_post(post_id)
    if not post:
        st.error("게시글을 찾을 수 없습니다.")
        return
        
    st.title(post.title)
    st.text(f"작��일: {post.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    st.text(f"수정일: {post.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("---")
    st.markdown(post.content)
    
    # 이미지가 있으면 표시
    if post.image_path and os.path.exists(post.image_path):
        st.image(post.image_path, caption="첨부 이미지")
    
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("수정"):
            st.query_params["mode"] = "edit"
            st.rerun()
    with col2:
        if st.button("삭제"):
            if delete_post(post_id):
                # 이미지 파일도 삭제
                if post.image_path and os.path.exists(post.image_path):
                    os.remove(post.image_path)
                st.success("게시글이 삭제되었습니다.")
                st.query_params.clear()
                st.rerun()
            else:
                st.error("삭제 중 오류가 발생했습니다.")
    with col3:
        if st.button("목록으로"):
            st.query_params.clear()
            st.rerun()

def render_post_form(board_type: str, post_id: int = None):
    """게시글 작성/수정 폼을 렌더링하는 함수"""
    post = get_post(post_id) if post_id else None
    
    title = st.text_input("제목", value=post.title if post else "")
    
    # 마크다운 가이드 표시
    with st.expander("마크다운 작성 가이드"):
        st.markdown("""
        ### 마크다운 작성 가이드
        ```
        # 제목 1
        ## 제목 2
        ### 제목 3
        
        **굵게** 또는 __굵게__
        *기울임* 또는 _기울임_
        
        - 목록 1
        - 목록 2
          - 하위 목록
        
        1. 번호 목록
        2. 번호 목록
        
        [링크](URL)
        
        ![이미지 설명](이미지URL)
        
        `코드`
        
        ```코드 블록```
        
        > 인용문
        ```
        """)
    
    content = st.text_area(
        "내 (마크다운 사용 가능)", 
        value=post.content if post else "", 
        height=300,
        help="마크다운 문법을 사용하여 작성할 수 있습니다. 위의 '마크다운 작성 가이드'를 참고하세요."
    )
    
    # 작성한 내용 미리보기
    if content:
        with st.expander("내용 미리보기"):
            st.markdown(content)
    
    # 이미지 업로드 필드
    uploaded_file = st.file_uploader("이미지 첨부", type=['png', 'jpg', 'jpeg'])
    
    # 기존 이미지 표시 (수정 모드일 경우)
    if post and post.image_path and os.path.exists(post.image_path):
        st.image(post.image_path, caption="현재 첨부된 이미지")
    
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("저장"):
            if not title or not content:
                st.error("제목과 내용을 모두 입력해주세요.")
                return
                
            # 이미지 처리
            image_path = None
            if uploaded_file:
                image_path = save_uploaded_image(uploaded_file)
                
            if post_id:
                update_post(post_id, title, content, image_path)
                st.success("게시글이 수정되었습니다.")
            else:
                add_post(title, content, board_type, image_path)
                st.success("게시글이 등록되었습니다.")
            
            st.query_params.clear()
            st.rerun()
    
    with col2:
        if st.button("취소"):
            st.query_params.clear()
            st.rerun()

def render_reflection_list():
    """회고 게시글 목록을 렌더링하는 함수"""
    st.title("회고 게시판")
    
    # 새 글 작성 버튼
    if st.button("✏️ 새 회고 작성"):
        st.query_params["mode"] = "write"
        st.rerun()
        
    # 게시글 목록 표시
    posts = get_posts("reflection")  # reflection 타입의 게시글 가져오기
    if posts.empty:
        st.info("등록된 회고가 없습니다.")
    else:
        for idx, post in posts.iterrows():
            # 회고일과 수정일 표시
            reflection_date = post['reflection_date'].strftime("%Y-%m-%d") if pd.notnull(post['reflection_date']) else "날짜 없음"
            display_date = post['updated_at'].strftime("%Y-%m-%d") if post['updated_at'] else post['created_at'].strftime("%Y-%m-%d")
            
            if st.button(f"📝 {post['title']} (회고일: {reflection_date}, 작성: {display_date})", key=f"post_{post['id']}"):
                st.query_params["post_id"] = str(post['id'])
                st.query_params["mode"] = "view"
                st.rerun()

def render_reflection_form(post_id: int = None):
    """회고 작성/수정 폼을 렌더링하는 함수"""
    post = get_post(post_id) if post_id else None
    
    title = st.text_input("제목", value=post.title if post else "")
    reflection_date = st.date_input(
        "회고일",
        value=post.reflection_date if post and post.reflection_date else datetime.now(pytz.timezone('Asia/Seoul')).date()
    )
    
    content = st.text_area(
        "내용 (마크다운 사용 가능)", 
        value=post.content if post else "", 
        height=300,
        help="마크다운 문법을 사용하여 작성할 수 있습니다."
    )
    
    # 작성한 내용 미리보기
    if content:
        with st.expander("내용 미리보기"):
            st.markdown(content)
    
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("저장"):
            if not title or not content:
                st.error("제목과 내용을 모두 입력해주세요.")
                return
                
            if post_id:
                update_post(post_id, title, content, reflection_date=reflection_date)
                st.success("회고가 수정되었습니다.")
            else:
                add_post(title, content, "reflection", reflection_date=reflection_date)
                st.success("회고가 등록되었습니다.")
            
            st.query_params.clear()
            st.rerun()
    
    with col2:
        if st.button("취소"):
            st.query_params.clear()
            st.rerun()

def render_reflection_detail(post_id: int):
    """회고 상세 보기를 렌더링하는 함수"""
    post = get_post(post_id)
    if not post:
        st.error("게시글을 찾을 수 없습니다.")
        return
        
    st.title(post.title)
    st.text(f"회고일: {post.reflection_date.strftime('%Y-%m-%d') if post.reflection_date else '날짜 없음'}")
    st.text(f"작성일: {post.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    if post.updated_at:
        st.text(f"수정일: {post.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("---")
    st.markdown(post.content)
    
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("수정"):
            st.query_params["mode"] = "edit"
            st.rerun()
    with col2:
        if st.button("삭제"):
            if delete_post(post_id):
                st.success("회고가 삭제되었습니다.")
                st.query_params.clear()
                st.rerun()
            else:
                st.error("삭제 중 오류가 발생했습니다.")
    with col3:
        if st.button("목록으로"):
            st.query_params.clear()
            st.rerun()
