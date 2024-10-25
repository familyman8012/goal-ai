import os
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Date,
    DateTime,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 데이터베이스 연결 설정
DATABASE_URL = f"postgresql://{os.getenv('DB_USERNAME')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

# SQLAlchemy 엔진 및 세션 설정
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# 모델 정의
class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    start_date = Column(Date)
    end_date = Column(Date)
    trigger_action = Column(String)
    importance = Column(Integer)
    memo = Column(Text)
    status = Column(String)
    category_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.now)


class GoalAnalysis(Base):
    __tablename__ = "goal_analyses"

    id = Column(Integer, primary_key=True, index=True)
    period = Column(String)  # "어제", "지난 주", "지난 달"
    goals_analyzed = Column(String)  # 분석된 목표들의 ID를 저장 (쉼표로 구분)
    analysis_result = Column(Text)  # GPT의 분석 결과
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
        if category_id is not None:
            category_id = int(category_id)
        goal = Goal(
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
    db = SessionLocal()
    try:
        query = "SELECT * FROM goals"
        return pd.read_sql_query(query, engine)
    except Exception as e:
        print(f"목표 조회 중 오류 발생: {e}")
        return pd.DataFrame()
    finally:
        db.close()


def update_goal(goal_id, **kwargs):
    db = SessionLocal()
    try:
        goal = db.query(Goal).filter(Goal.id == goal_id).first()
        for key, value in kwargs.items():
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
        # 표 ID들을 정렬하여 문자열로 변환
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
        category = Category(name=name)
        db.add(category)
        db.commit()
        db.refresh(category)
        return category
    finally:
        db.close()


def get_categories():
    db = SessionLocal()
    try:
        query = "SELECT * FROM categories ORDER BY name"
        return pd.read_sql_query(query, engine)
    finally:
        db.close()


def update_category(category_id: int, name: str):
    db = SessionLocal()
    try:
        category = (
            db.query(Category).filter(Category.id == category_id).first()
        )
        category.name = name
        db.commit()
    finally:
        db.close()


def delete_category(category_id: int):
    db = SessionLocal()
    try:
        category = (
            db.query(Category).filter(Category.id == category_id).first()
        )
        db.delete(category)
        db.commit()
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
