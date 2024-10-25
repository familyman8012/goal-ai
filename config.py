import os
from dotenv import load_dotenv

load_dotenv()

# 필수 환경 변수 검증 추가
required_env_vars = [
    "OPENAI_API_KEY",
    "DB_HOST",
    "DB_PORT",
    "DB_USERNAME",
    "DB_PASSWORD",
    "DB_NAME",
    "PPLX_API_KEY",  # 추가
]

for var in required_env_vars:
    if not os.getenv(var):
        raise ValueError(f"필수 환경 변수가 설정되지 않았습니다: {var}")

# OpenAI API 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY").strip()

# 데이터베이스 설정
DATABASE_NAME = "goals.db"

# 목표 상태 정의
GOAL_STATUS = ["진행 전", "진행 중", "완료"]

# 중요도 옵션
IMPORTANCE_LEVELS = list(range(1, 11))
