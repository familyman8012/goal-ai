import os
from dotenv import load_dotenv
import streamlit as st

# 환경 변수 가져오기
def get_env_var(var_name: str) -> str:
    if hasattr(st, "secrets"):  # Streamlit Cloud 환경
        # API 키는 api_keys 섹션에서 가져옴
        if var_name in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "PPLX_API_KEY"]:
            return st.secrets["api_keys"][var_name]
        # 데이터베이스 관련 변수는 postgres 섹션에서 가져옴
        elif var_name in ["DB_HOST", "DB_PORT", "DB_USERNAME", "DB_PASSWORD", "DB_NAME"]:
            return st.secrets["postgres"][var_name]
    else:  # 로컬 환경
        load_dotenv()
        return os.getenv(var_name)

# 필수 환경 변수 검증
required_env_vars = [
    "OPENAI_API_KEY",
    "DB_HOST",
    "DB_PORT",
    "DB_USERNAME",
    "DB_PASSWORD",
    "DB_NAME",
    "PPLX_API_KEY",
]

for var in required_env_vars:
    if not get_env_var(var):
        raise ValueError(f"필수 환경 변수가 설정되지 않았습니다: {var}")

# OpenAI API 설정
OPENAI_API_KEY = get_env_var("OPENAI_API_KEY").strip()

# 데이터베이스 설정
DATABASE_NAME = "goals.db"

# 목표 상태 정의
GOAL_STATUS = ["진행 전", "진행 중", "완료"]

# 중요도 옵션
IMPORTANCE_LEVELS = list(range(1, 11))
