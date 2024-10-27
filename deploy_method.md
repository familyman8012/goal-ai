# 목표 달성 GPT Streamlit Cloud 배포 가이드

## 1. 사전 준비

### 1.1 GitHub 저장소 설정
1. GitHub에 새 저장소 생성
2. 로컬 코드를 GitHub 저장소에 푸시
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-github-repo-url>
git push -u origin main
```

### 1.2 requirements.txt 생성
```bash
pip freeze > requirements.txt
```

필수 패키지 목록:
```text
streamlit
sqlalchemy
psycopg2-binary
python-dotenv
langchain
langchain-openai
langchain-anthropic
langchain-google-genai
bcrypt
streamlit-cookies-controller
```

## 2. AWS RDS 데이터베이스 설정

### 2.1 보안 그룹 설정
1. AWS RDS 보안 그룹에서 인바운드 규칙 추가
   - Streamlit Cloud의 IP 범위 허용
   - PostgreSQL 포트(5432) 개방

### 2.2 데이터베이스 연결 테스트
```python
import psycopg2

conn = psycopg2.connect(
    host="your-rds-endpoint",
    database="your-db-name",
    user="your-username",
    password="your-password"
)
```

## 3. Streamlit Cloud 배포

### 3.1 Streamlit Cloud 설정
1. https://streamlit.io/cloud 접속
2. GitHub 계정으로 로그인
3. "New app" 클릭
4. 배포할 GitHub 저장소 선택
   - Repository: `<your-github-repo>`
   - Branch: `main`
   - Main file path: `Home.py`

### 3.2 환경 변수 설정
Streamlit Cloud의 Secrets 관리에서 다음 환경 변수 설정:
```toml
[postgres]
DB_HOST = "your-rds-endpoint"
DB_PORT = "5432"
DB_USERNAME = "your-username"
DB_PASSWORD = "your-password"
DB_NAME = "your-db-name"

[api_keys]
OPENAI_API_KEY = "your-openai-key"
ANTHROPIC_API_KEY = "your-anthropic-key"
GOOGLE_API_KEY = "your-google-key"
PPLX_API_KEY = "your-perplexity-key"
```

### 3.3 배포 확인
1. Deploy 버튼 클릭
2. 배포 로그 확인
3. 생성된 URL로 접속하여 앱 테스트

## 4. 문제 해결

### 4.1 일반적인 문제
1. 데이터베이스 연결 오류
   - AWS RDS 보안 그룹 설정 확인
   - 데이터베이스 자격 증명 확인
   
2. 패키지 설치 오류
   - requirements.txt 버전 호환성 확인
   - 불필요한 패키지 제거

3. API 키 관련 오류
   - Streamlit Secrets 설정 확인
   - API 키 유효성 검증

### 4.2 로그 확인
- Streamlit Cloud 대시보드에서 앱 로그 확인
- 오류 메시지 분석 및 문제 해결

## 5. 유지보수

### 5.1 업데이트 배포
1. 로컬에서 코드 수정
2. GitHub에 변경사항 푸시
```bash
git add .
git commit -m "Update description"
git push origin main
```
3. Streamlit Cloud가 자동으로 재배포

### 5.2 모니터링
- Streamlit Cloud 대시보드에서 앱 상태 모니터링
- 리소스 사용량 확인
- 오류 로그 주기적 확인
