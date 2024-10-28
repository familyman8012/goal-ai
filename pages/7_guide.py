import streamlit as st


st.set_page_config(
    page_title="사용자 가이드",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="collapsed",  # "expanded"에서 "collapsed"로 변경
    menu_items=None
)

# CSS로 사이드바 버튼 숨기기
st.markdown(
    """
    <style>
        [data-testid="collapsedControl"] {
            visibility: hidden;
        }
    </style>
    """,
    unsafe_allow_html=True
)
from utils.session_utils import clear_goal_session
from utils.auth_utils import login_required, init_auth
from utils.menu_utils import show_menu

# 인증 초기화
init_auth()

# 로그인 체크
login_required()

# 페이지 진입 시 세션 정리
clear_goal_session()

# 메뉴 표시 추가
show_menu()


st.title("사용자 가이드")

st.markdown("""
## 💬 기본 대화 기능
AI 컨설턴트와 자연스러운 대화를 나눌 수 있습니다. 목표 설정이나 일상적인 대화 모두 가능합니다.

## 🔍 검색 기능
검색어 뒤에 "검색해줘"를 붙여서 사용합니다.
```
예시:
- "2024년 개봉 영화 검색해줘"
- "파이썬 강의 추천 검색해줘"
```

### 검색 결과 저장
검색 후 정보 게시판에 저장할 수 있습니다.
```
예시:
- "방금 검색 결과 정보 게시판에 올려줘"
- "방금 검색 결과 제목은 2024 상반기 개봉 영화로 정보 게시판에 올려줘"
```

### 일반 정보 저장
검색 결과가 아닌 일반 텍스트도 정보 게시판에 저장할 수 있습니다.
```
예시:
- "올해 하반기 취업준비생들이 자기소개서를 가장 많이 작성한 기업은 현대차로 나타났다를 정보 게시판에 올려줘"
- "제목은 취업 동향으로 올해 하반기 취업준비생들이 자기소개서를 가장 많이 작성한 기업은 현대차로 나타났다를 정보 게시판에 올려줘"
```

## 📋 목표 관리
### 목표 추가
자연스러운 대화로 목표를 추가할 수 있습니다.
```
예시:
- "커리어에 타입스크립트 공부 추가해줘"
- "운동 목표에 매주 수요일 저녁 요가 추가해줘"
- "다음 달까지 책 3권 읽기 목표 추가해줘"
```

### 반복 목표 설정
특정 요일에 반복되는 목표를 설정할 수 있습니다.
```
예시:
- "매주 월,수,금 아침 러닝하기 추가해줘"
- "매주 화요일 저녁 스터디 참석 추가해줘"
```

## 📊 카테고리 관리
목표를 체계적으로 관리하기 위한 카테고리를 설정할 수 있습니다.
- 카테고리 추가/수정/삭제 가능
- 목표 추가 시 카테고리 지정 가능

## 📝 게시판 기능
### 정보 게시판
- 유용한 정보나 검색 결과를 저장
- 검색 결과 자동 저장 기능

### 아이디어 게시판
- 새로운 아이디어나 계획을 기록
- 이미지 첨부 가능
 ```
예시:
- 내일 모임하나 신청해야겠다를 아이디어 게시판에 올려줘
```

## 🔄 목표 분석
- 미달성 목표에 대한 AI 분석
- 기간별 목표 달성률 확인
- AI의 맞춤형 조언 제공
""")

# 사이드바에 모델 설명 추가
st.sidebar.markdown("""
## 🤖 AI 모델 설명

### GPT-4
- 가장 강력한 성능
- 복잡한 대화와 분석에 적합

### Claude-3
- 자연스러운 대화
- 빠른 응답 속도

### Gemini
- 효율적인 정보 처리
- 간단한 대에 적합
""")
