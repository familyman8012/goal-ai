import os
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Date,
    DateTime,
    Text,
    func,
    text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date
import pandas as pd
import streamlit as st
import pytz


# 데이터베이스 연결 정보
def get_database_url():
    if hasattr(st, "secrets"):  # Streamlit Cloud 환경
        return (
            "postgresql://"
            f"{st.secrets.postgres.DB_USERNAME}:"
            f"{st.secrets.postgres.DB_PASSWORD}@"
            f"{st.secrets.postgres.DB_HOST}:"
            f"{st.secrets.postgres.DB_PORT}/"
            f"{st.secrets.postgres.DB_NAME}"
        )
    else:  # 로컬 환경
        from dotenv import load_dotenv

        load_dotenv()

        return (
            "postgresql://"
            f"{os.getenv('DB_USERNAME')}:"
            f"{os.getenv('DB_PASSWORD')}@"
            f"{os.getenv('DB_HOST')}:"
            f"{os.getenv('DB_PORT')}/"
            f"{os.getenv('DB_NAME')}"
        )


DATABASE_URL = get_database_url()

# SQLAlchemy 엔진 및 세션 설정
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# 모델 정의
class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # user_id 필드 추가
    title = Column(String, nullable=False)
    start_date = Column(DateTime)  # Date에서 DateTime으로 변경
    end_date = Column(DateTime)  # Date에서 DateTime으로 변경
    trigger_action = Column(String)
    importance = Column(Integer)
    memo = Column(Text)
    status = Column(String)
    category_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)  # unique=True 제거
    created_at = Column(DateTime, default=datetime.now)


class GoalAnalysis(Base):
    __tablename__ = "goal_analyses"

    id = Column(Integer, primary_key=True, index=True)
    period = Column(String)  # "어제", "지난 주", "지난 달"
    goals_analyzed = Column(String)  # 분석된 목표들의 ID를 저장 (쉼표로 구분)
    analysis_result = Column(Text)  # GPT의 분석 결과
    created_at = Column(DateTime, default=datetime.now)


class Board(Base):
    __tablename__ = "boards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # user_id 필드 추가
    title = Column(String, nullable=False)
    content = Column(Text)
    image_path = Column(String)  # 이미지 경로 저장
    board_type = Column(String, nullable=False)  # 'info' 또는 'idea'
    reflection_date = Column(Date)  # 추가
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # user_id 필드 추가
    site_name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class UserProfile(Base):
    __tablename__ = "user_profile"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)  # user_id 컬럼 추가
    content = Column(Text)
    consultant_style = Column(Text)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# User 모델 추가
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)


# Session 모델 추가
class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, nullable=False)
    session_token = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)


# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)


# CRUD 함수들
def get_db():
    try:
        db = SessionLocal()
        return db
    finally:
        db.close()


def add_goal(
    title,
    start_date=None,
    end_date=None,
    trigger_action="",
    importance=5,
    memo="",
    status="진행 전",
    category_id=None,
):
    db = get_db()
    try:
        # timezone 처리
        kst = pytz.timezone("Asia/Seoul")

        # 입력받은 datetime이 이미 timezone 정보를 가지고 있다면 KST로 변환
        if start_date:
            if start_date.tzinfo:
                start_date = start_date.astimezone(kst)
            else:
                start_date = kst.localize(start_date)
            # UTC로 변환하여 저장
            start_date = start_date.astimezone(pytz.UTC)

        if end_date:
            if end_date.tzinfo:
                end_date = end_date.astimezone(kst)
            else:
                end_date = kst.localize(end_date)
            # UTC로 변환하여 저장
            end_date = end_date.astimezone(pytz.UTC)

        # category_id를 int로 변환
        if category_id is not None:
            category_id = int(category_id)

        goal = Goal(
            user_id=st.session_state.user_id,
            title=title,
            start_date=start_date,
            end_date=end_date,
            trigger_action=trigger_action,
            importance=importance,
            memo=memo,
            status=status,
            category_id=category_id,
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)
        return goal
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_goals():
    """현재 로그인한 사용자의 목표만 조회"""
    db = SessionLocal()
    try:
        kst = pytz.timezone("Asia/Seoul")
        goals = (
            db.query(Goal)
            .filter(Goal.user_id == st.session_state.user_id)
            .all()
        )

        # 결과를 DataFrame으로 변환하기 전에 timezone 처리
        goals_data = []
        for goal in goals:
            # UTC에서 KST로 변환
            start_date = (
                goal.start_date.replace(tzinfo=pytz.UTC).astimezone(kst)
                if goal.start_date
                else None
            )
            end_date = (
                goal.end_date.replace(tzinfo=pytz.UTC).astimezone(kst)
                if goal.end_date
                else None
            )

            goal_dict = {
                "id": goal.id,
                "title": goal.title,
                "start_date": start_date,
                "end_date": end_date,
                "trigger_action": goal.trigger_action,
                "importance": goal.importance,
                "memo": goal.memo,
                "status": goal.status,
                "category_id": goal.category_id,
                "created_at": goal.created_at,
            }
            goals_data.append(goal_dict)

        return pd.DataFrame(goals_data)
    finally:
        db.close()


def update_goal(goal_id, **kwargs):
    db = SessionLocal()
    try:
        goal = db.query(Goal).filter(Goal.id == goal_id).first()

        # timezone 처리
        kst = pytz.timezone("Asia/Seoul")

        for key, value in kwargs.items():
            # start_date와 end_date에 대해 timezone 처리
            if key in ["start_date", "end_date"] and value:
                if value.tzinfo:
                    value = value.astimezone(kst)
                else:
                    value = kst.localize(value)
                # UTC로 변환하여 저장
                value = value.astimezone(pytz.UTC)

            # category_id를 int로 변환
            if key == "category_id" and value is not None:
                value = int(value)

            setattr(goal, key, value)

        db.commit()
    finally:
        db.close()


def add_goal_analysis(period, goals_analyzed, analysis_result):
    db = SessionLocal()
    try:
        analysis = GoalAnalysis(
            period=period,
            goals_analyzed=",".join(map(str, goals_analyzed)),
            analysis_result=analysis_result,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis
    finally:
        db.close()


def get_goal_analysis(period, goals_analyzed):
    db = SessionLocal()
    try:
        # 표 ID들을 정렬하여 자열로 변환
        goals_str = ",".join(map(str, sorted(goals_analyzed)))

        # 최신 분석 결과 조합
        analysis = (
            db.query(GoalAnalysis)
            .filter(GoalAnalysis.period == period)
            .filter(GoalAnalysis.goals_analyzed == goals_str)
            .order_by(GoalAnalysis.created_at.desc())
            .first()
        )

        return analysis
    finally:
        db.close()


# 카테고리 관련 함수들
def add_category(name: str):
    db = SessionLocal()
    try:
        category = Category(
            user_id=st.session_state.user_id, name=name  # 사용자 ID 추가
        )
        db.add(category)
        db.commit()
        db.refresh(category)
        return category
    finally:
        db.close()


def get_categories():
    db = SessionLocal()
    try:
        query = """
        SELECT * FROM categories 
        WHERE user_id = %(user_id)s 
        ORDER BY name
        """
        return pd.read_sql_query(
            query, engine, params={"user_id": st.session_state.user_id}
        )
    finally:
        db.close()


def update_category(category_id: int, name: str):
    db = SessionLocal()
    try:
        category = (
            db.query(Category)
            .filter(Category.id == category_id)
            .filter(
                Category.user_id == st.session_state.user_id
            )  # 사용자 확인
            .first()
        )
        if category:
            category.name = name
            db.commit()
            return True
        return False
    finally:
        db.close()


def delete_category(category_id: int):
    db = SessionLocal()
    try:
        category = (
            db.query(Category)
            .filter(Category.id == category_id)
            .filter(
                Category.user_id == st.session_state.user_id
            )  # 사용자 확인
            .first()
        )
        if category:
            db.delete(category)
            db.commit()
            return True
        return False
    finally:
        db.close()


def delete_goal(goal_id: int):
    """목표를 삭제하는 함수"""
    db = SessionLocal()
    try:
        goal = db.query(Goal).filter(Goal.id == goal_id).first()
        if goal:
            db.delete(goal)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        print(f"목표 삭제 중 오류 발생: {e}")
        return False
    finally:
        db.close()


# 게시판 관련 CRUD 함수들
def add_post(
    title: str,
    content: str,
    board_type: str,
    image_path: str = None,
    reflection_date: date = None,
):
    """게시글을 추가하는 함수"""
    db = SessionLocal()
    try:
        post = Board(
            user_id=st.session_state.user_id,
            title=title,
            content=content,
            board_type=board_type,
            image_path=image_path,
            reflection_date=reflection_date,
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        return post
    finally:
        db.close()


def get_posts(board_type: str):
    db = SessionLocal()
    try:
        query = """
        SELECT * FROM boards 
        WHERE board_type = %(board_type)s 
        AND user_id = %(user_id)s 
        ORDER BY reflection_date DESC, created_at DESC
        """
        return pd.read_sql_query(
            query,
            engine,
            params={
                "board_type": board_type,
                "user_id": st.session_state.user_id,
            },
        )
    finally:
        db.close()


def get_post(post_id: int):
    db = SessionLocal()
    try:
        return (
            db.query(Board)
            .filter(Board.id == post_id)
            .filter(Board.user_id == st.session_state.user_id)  # 사용자 확인
            .first()
        )
    finally:
        db.close()


def update_post(
    post_id: int,
    title: str,
    content: str,
    image_path: str = None,
    reflection_date: date = None,
):
    """게시글을 수정하는 함수"""
    db = SessionLocal()
    try:
        post = (
            db.query(Board)
            .filter(Board.id == post_id)
            .filter(Board.user_id == st.session_state.user_id)
            .first()
        )
        if post:
            post.title = title
            post.content = content
            if image_path:
                post.image_path = image_path
            if reflection_date:
                post.reflection_date = reflection_date
            post.updated_at = datetime.now()
            db.commit()
            return post
        return None
    finally:
        db.close()


def delete_post(post_id: int):
    db = SessionLocal()
    try:
        post = (
            db.query(Board)
            .filter(Board.id == post_id)
            .filter(Board.user_id == st.session_state.user_id)  # 사용자 확인
            .first()
        )
        if post:
            db.delete(post)
            db.commit()
            return True
        return False
    finally:
        db.close()


def add_recurring_goals(
    title,
    dates,
    trigger_action="",
    importance=5,
    memo="",
    status="진행 전",
    category_id=None,
):
    """여러 날짜에 대해 동일한 목표를 추가하는 함수"""
    db = get_db()
    try:
        for date in dates:
            goal = Goal(
                title=title,
                start_date=date,
                end_date=date,
                trigger_action=trigger_action,
                importance=importance,
                memo=memo,
                status=status,
                category_id=category_id,
            )
            db.add(goal)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


# CRUD 함수 추가
def add_link(site_name: str, url: str):
    db = SessionLocal()
    try:
        link = Link(
            user_id=st.session_state.user_id,  # 사용자 ID 추가
            site_name=site_name,
            url=url,
        )
        db.add(link)
        db.commit()
        db.refresh(link)
        return link
    finally:
        db.close()


def get_links():
    db = SessionLocal()
    try:
        query = """
        SELECT * FROM links 
        WHERE user_id = %(user_id)s 
        ORDER BY created_at DESC
        """
        return pd.read_sql_query(
            query, engine, params={"user_id": st.session_state.user_id}
        )
    finally:
        db.close()


def get_link(link_id: int):
    db = SessionLocal()
    try:
        return (
            db.query(Link)
            .filter(Link.id == link_id)
            .filter(Link.user_id == st.session_state.user_id)  # 사용자 확인
            .first()
        )
    finally:
        db.close()


def update_link(link_id: int, site_name: str, url: str):
    db = SessionLocal()
    try:
        link = (
            db.query(Link)
            .filter(Link.id == link_id)
            .filter(Link.user_id == st.session_state.user_id)  # 사용자 확인
            .first()
        )
        if link:
            link.site_name = site_name
            link.url = url
            db.commit()
            return link
        return None
    finally:
        db.close()


def delete_link(link_id: int):
    db = SessionLocal()
    try:
        link = (
            db.query(Link)
            .filter(Link.id == link_id)
            .filter(Link.user_id == st.session_state.user_id)  # 사용자 확인
            .first()
        )
        if link:
            db.delete(link)
            db.commit()
            return True
        return False
    finally:
        db.close()


# 사용자 프로필 관련 함수들
def get_user_profile():
    """사용자 프로필 정보를 가져오는 함수"""
    db = SessionLocal()
    try:
        profile = (
            db.query(UserProfile)
            .filter(
                UserProfile.user_id == st.session_state.user_id
            )  # 사용자 확인
            .first()
        )
        if profile:
            return {
                "content": profile.content,
                "consultant_style": profile.consultant_style,
            }
        return {}
    finally:
        db.close()


def update_user_profile(profile_data):
    """용자 프로필을 업데이트하는 함수"""
    db = SessionLocal()
    try:
        profile = (
            db.query(UserProfile)
            .filter(
                UserProfile.user_id == st.session_state.user_id
            )  # 사용자 확인
            .first()
        )
        if not profile:
            profile = UserProfile(
                user_id=st.session_state.user_id
            )  # 새 프로필 생성 시 사용자 ID 추가
            db.add(profile)

        for key, value in profile_data.items():
            setattr(profile, key, value)

        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_todays_goals():
    """오늘의 목표를 져오 함수"""
    db = SessionLocal()
    try:
        today = datetime.now().date()
        return (
            db.query(Goal)
            .filter(Goal.user_id == st.session_state.user_id)  # 사용자 확인
            .filter(func.date(Goal.start_date) <= today)
            .filter(func.date(Goal.end_date) >= today)
            .all()
        )
    finally:
        db.close()


def get_incomplete_goals():
    """미완료된 목표를 가져오는 함수"""
    db = SessionLocal()
    try:
        today = datetime.now().date()
        return (
            db.query(Goal)
            .filter(Goal.user_id == st.session_state.user_id)  # 사용자 확인
            .filter(func.date(Goal.end_date) < today)
            .filter(Goal.status != "완료")
            .all()
        )
    finally:
        db.close()


def get_category_name(category_id: int) -> str:
    """카테고 ID로 카테고리 이름을 져오는 함수"""
    db = SessionLocal()
    try:
        category = (
            db.query(Category).filter(Category.id == category_id).first()
        )
        return category.name if category else "미분류"
    finally:
        db.close()


def create_user(username: str, email: str, password_hash: str) -> int:
    """새로운 사용자를 생하는 함수"""
    db = SessionLocal()
    try:
        query = text(
            """
        INSERT INTO users (username, email, password_hash)
        VALUES (:username, :email, :password_hash)
        RETURNING id
        """
        )
        result = db.execute(
            query,
            {
                "username": username,
                "email": email,
                "password_hash": password_hash,
            },
        )
        user_id = result.scalar()
        db.commit()
        return user_id  # user_id 반환
    except Exception as e:
        db.rollback()
        print(f"Error creating user: {e}")
        return None
    finally:
        db.close()


def create_initial_profile(user_id: int):
    """새 사용자의 초기 프로필을 생성하는 함수"""
    db = SessionLocal()
    try:
        profile = UserProfile(user_id=user_id, content="", consultant_style="")
        db.add(profile)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error creating initial profile: {e}")
    finally:
        db.close()


def get_user_by_credentials(email: str) -> dict:
    """이메일로 사용자 인증 정보를 조회하는 함수"""
    db = SessionLocal()
    try:
        query = text(
            """
        SELECT id, email, username, password_hash, is_active
        FROM users
        WHERE email = :email
        """
        )
        result = db.execute(query, {"email": email}).fetchone()
        if result:
            return {
                "id": result[0],
                "email": result[1],
                "username": result[2],
                "password_hash": result[3],
                "is_active": result[4],
            }
        return None
    finally:
        db.close()


def get_user_by_email(email: str) -> dict:
    """이메일로 사용자를 조회하는 함수"""
    db = SessionLocal()
    try:
        query = text(
            """
        SELECT id, email, username
        FROM users
        WHERE email = :email
        """
        )
        result = db.execute(query, {"email": email}).fetchone()
        if result:
            return {"id": result[0], "email": result[1], "username": result[2]}
        return None
    finally:
        db.close()


def update_last_login(user_id: int):
    """마지막 로그인 시간을 업데이트하는 함수"""
    db = SessionLocal()
    try:
        query = text(
            """
        UPDATE users
        SET last_login = :last_login
        WHERE id = :user_id
        """
        )
        db.execute(query, {"last_login": datetime.now(), "user_id": user_id})
        db.commit()
    finally:
        db.close()


def update_session(user_id: int, session_token: str, expires_at: datetime):
    """세션 정보를 업데이트하는 함수"""
    db = SessionLocal()
    try:
        # 기존 세션이 있으면 업데이트, 없으면 새로 생성
        query = text(
            """
        INSERT INTO sessions (user_id, session_token, expires_at)
        VALUES (:user_id, :session_token, :expires_at)
        ON CONFLICT (user_id) 
        DO UPDATE SET 
            session_token = :session_token,
            expires_at = :expires_at,
            last_activity = CURRENT_TIMESTAMP
        """
        )
        db.execute(
            query,
            {
                "user_id": user_id,
                "session_token": session_token,
                "expires_at": expires_at,
            },
        )
        db.commit()
    finally:
        db.close()


def get_session(session_token: str):
    """세션 토큰으로 세션 정보를 조회하는 함수"""
    db = SessionLocal()
    try:
        query = text(
            """
        SELECT user_id, expires_at 
        FROM sessions 
        WHERE session_token = :token 
        AND expires_at > CURRENT_TIMESTAMP
        """
        )
        result = db.execute(query, {"token": session_token}).fetchone()
        return result if result else None
    finally:
        db.close()


def validate_session_token(session_token: str) -> bool:
    """세션 토큰의 유효성을 검사하는 함수"""
    db = SessionLocal()
    try:
        query = text(
            """
        SELECT EXISTS (
            SELECT 1 FROM sessions 
            WHERE session_token = :token 
            AND expires_at > CURRENT_TIMESTAMP
        )
        """
        )
        result = db.execute(query, {"token": session_token}).scalar()
        return bool(result)
    finally:
        db.close()


def delete_session(session_token: str):
    """세션을 삭제하는 함수"""
    db = SessionLocal()
    try:
        query = text(
            """
        DELETE FROM sessions 
        WHERE session_token = :token
        """
        )
        db.execute(query, {"token": session_token})
        db.commit()
    finally:
        db.close()


def get_user_by_id(user_id: int) -> dict:
    """사용자 ID로 사용자 정보를 조회하는 함수"""
    db = SessionLocal()
    try:
        query = text(
            """
        SELECT id, username, email
        FROM users
        WHERE id = :user_id
        """
        )
        result = db.execute(query, {"user_id": user_id}).fetchone()
        if result:
            return {"id": result[0], "username": result[1], "email": result[2]}
        return None
    finally:
        db.close()


# 대화 게시판 테이블 생성 쿼리 추가
def create_tables():
    # ... 기존 테이블 생성 코드 ...

    # 대화 게시판 테이블 생성
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_history (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            title VARCHAR(200),
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """
    )


# 대화 저장 함수
def add_chat_history(user_id: int, title: str, content: str) -> int:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO chat_history (user_id, title, content)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (user_id, title, content),
            )
            chat_id = cur.fetchone()[0]
            conn.commit()
            return chat_id


# 대화 기록 조회 함수
def get_chat_histories(user_id: int = None, limit: int = None):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            query = """
                SELECT ch.id, ch.title, ch.content, ch.created_at, u.username
                FROM chat_history ch
                JOIN users u ON ch.user_id = u.id
            """
            if user_id:
                query += " WHERE ch.user_id = %s"
            query += " ORDER BY ch.created_at DESC"
            if limit:
                query += f" LIMIT {limit}"

            if user_id:
                cur.execute(query, (user_id,))
            else:
                cur.execute(query)

            return cur.fetchall()
