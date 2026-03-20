"""
Database Models
================

SQLAlchemy ORM models — full real-time schema.
Implements the APXMIND Real-Time Data Schema Blueprint.

Backward-compat notes:
  - All columns added to existing tables are nullable or have defaults so
    `create_all` can run against an existing populated SQLite DB.
  - Legacy columns (e.g. users.name unique=True, users.daily_study_target,
    lessons.order/estimated_time) are preserved alongside their blueprint
    equivalents.
  - quiz_attempts (old standalone table) is kept as-is; the new quiz flow
    uses quizzes / quiz_questions / quiz_attempt_answers / quiz_attempt_summaries.
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


# ============================================================================
# BASE
# ============================================================================

class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


# ============================================================================
# ENUMS  (kept for places that still import them)
# ============================================================================

class SubjectEnum(str, PyEnum):
    BIOLOGY = "biology"
    CHEMISTRY = "chemistry"
    PHYSICS = "physics"


class DifficultyEnum(str, PyEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class LearningLevelEnum(str, PyEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


# ============================================================================
# 3.1  IDENTITY & PROFILE
# ============================================================================

class User(Base):
    """Student user — extended to match blueprint while keeping legacy cols."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Blueprint fields
    username = Column(String(50), unique=True, nullable=True, index=True)
    name = Column(String(100), nullable=False, index=True)          # still unique in existing DBs
    email = Column(String(120), unique=True, nullable=True, index=True)
    password_hash = Column(String(256), nullable=True)
    avatar_url = Column(Text, nullable=True)
    dob = Column(String(20), nullable=True)
    current_class = Column(String(20), nullable=True, default="12th")
    attempt_number = Column(SmallInteger, nullable=True, default=1)
    target_year = Column(SmallInteger, nullable=True)
    target_score = Column(SmallInteger, nullable=True, default=650)
    daily_study_target_hours = Column(Numeric(4, 1), nullable=True, default=4)
    preferred_language = Column(String(20), nullable=True, default="english")
    learning_level = Column(String(20), nullable=True, default="beginner")
    timezone = Column(String(64), nullable=True, default="Asia/Kolkata")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_active_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    # Legacy columns (kept for backward compat)
    strong_subjects = Column(JSON, nullable=True, default=list)
    weak_subjects = Column(JSON, nullable=True, default=list)
    daily_study_target = Column(Integer, nullable=True, default=4)
    last_active = Column(DateTime, nullable=True)

    # Relationships — new tables
    subject_preferences = relationship(
        "UserSubjectPreference", back_populates="user", cascade="all, delete-orphan"
    )
    learning_events = relationship(
        "LearningEvent", back_populates="user", cascade="all, delete-orphan"
    )
    daily_progress_rows = relationship(
        "DailyProgress", back_populates="user", cascade="all, delete-orphan"
    )
    gamification_snapshot = relationship(
        "UserGamificationSnapshot", back_populates="user",
        uselist=False, cascade="all, delete-orphan"
    )
    badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="user", cascade="all, delete-orphan")
    learning_sessions = relationship(
        "LearningSession", back_populates="user", cascade="all, delete-orphan"
    )
    query_events = relationship(
        "QueryEvent", back_populates="user", cascade="all, delete-orphan"
    )
    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")
    study_notes = relationship("StudyNote", back_populates="user", cascade="all, delete-orphan")
    topic_mastery = relationship(
        "TopicMastery", back_populates="user", cascade="all, delete-orphan"
    )
    recommendations = relationship(
        "LearningRecommendation", back_populates="user", cascade="all, delete-orphan"
    )
    readiness_snapshots = relationship(
        "ExamReadinessSnapshot", back_populates="user", cascade="all, delete-orphan"
    )
    habit_signals = relationship(
        "HabitSignal", back_populates="user", cascade="all, delete-orphan"
    )

    # Relationships — legacy tables
    progress = relationship("Progress", back_populates="user", cascade="all, delete-orphan")
    quiz_attempts = relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "email": self.email,
            "avatar_url": self.avatar_url,
            "dob": self.dob,
            "current_class": self.current_class,
            "attempt_number": self.attempt_number,
            "target_year": self.target_year,
            "target_score": self.target_score,
            "daily_study_target_hours": (
                float(self.daily_study_target_hours)
                if self.daily_study_target_hours is not None else None
            ),
            "preferred_language": self.preferred_language,
            "learning_level": self.learning_level,
            "timezone": self.timezone,
            "strong_subjects": self.strong_subjects or [],
            "weak_subjects": self.weak_subjects or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
        }


class UserSubjectPreference(Base):
    """Per-subject strength & priority rank for a user."""
    __tablename__ = "user_subject_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "subject", name="uq_user_subject_pref"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(20), nullable=False)        # physics / chemistry / biology
    strength = Column(String(10), nullable=False)       # strong / weak / neutral
    priority_rank = Column(SmallInteger, nullable=True) # 1 = highest

    user = relationship("User", back_populates="subject_preferences")


# ============================================================================
# 3.2  CONTENT CATALOG
# ============================================================================

class Subject(Base):
    """NEET subject.
    Blueprint uses 'code'; existing DB uses 'name'. Both are kept.
    """
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(20), unique=True, nullable=False, index=True)   # legacy PK-style identifier
    code = Column(String(20), unique=True, nullable=True, index=True)    # blueprint field (= name for NEET)
    display_name = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    color = Column(String(20), nullable=True)
    total_lessons = Column(Integer, nullable=True, default=0)

    topics = relationship("Topic", back_populates="subject", cascade="all, delete-orphan")
    lessons = relationship("Lesson", back_populates="subject", cascade="all, delete-orphan")
    content_resources = relationship(
        "ContentResource", back_populates="subject", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code or self.name,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "total_lessons": self.total_lessons,
        }


class Topic(Base):
    """Syllabus topic within a subject."""
    __tablename__ = "topics"
    __table_args__ = (
        UniqueConstraint("subject_id", "name", name="uq_subject_topic"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    syllabus_weight = Column(Numeric(5, 2), nullable=True)  # % weight in NEET

    subject = relationship("Subject", back_populates="topics")
    lessons = relationship("Lesson", back_populates="topic")


class Lesson(Base):
    """Lesson under a subject and optionally a topic."""
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)  # blueprint field
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    difficulty = Column(String(20), nullable=False, default="medium")
    sequence_no = Column(Integer, nullable=True)          # blueprint field
    order = Column(Integer, nullable=True)                # legacy alias
    estimated_minutes = Column(Integer, nullable=True, default=30)  # blueprint field
    estimated_time = Column(Integer, nullable=True, default=30)     # legacy alias
    topics = Column(JSON, nullable=True, default=list)   # legacy JSON array of topic strings

    subject = relationship("Subject", back_populates="lessons")
    topic = relationship("Topic", back_populates="lessons")
    progress = relationship("Progress", back_populates="lesson", cascade="all, delete-orphan")
    content_resources = relationship("ContentResource", back_populates="lesson")

    def to_dict(self):
        return {
            "id": self.id,
            "subject_id": self.subject_id,
            "subject_name": self.subject.name if self.subject else None,
            "topic_id": self.topic_id,
            "title": self.title,
            "description": self.description,
            "difficulty": self.difficulty,
            "sequence_no": self.sequence_no if self.sequence_no is not None else self.order,
            "order": self.order if self.order is not None else self.sequence_no,
            "estimated_minutes": (
                self.estimated_minutes if self.estimated_minutes is not None
                else self.estimated_time
            ),
            "topics": self.topics or [],
        }


class ContentResource(Base):
    """Attachable learning resource (NCERT PDF, video, PYQ set, etc.)."""
    __tablename__ = "content_resources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)    # NULL = subject-level
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    resource_type = Column(String(30), nullable=False)  # ncert/chapter/pyq/video/note
    title = Column(String(255), nullable=False)
    source_path = Column(Text, nullable=False)
    meta = Column(JSON, nullable=True)

    lesson = relationship("Lesson", back_populates="content_resources")
    subject = relationship("Subject", back_populates="content_resources")


# ============================================================================
# 3.3  REAL-TIME ACTIVITY EVENT LAYER  (append-only)
# ============================================================================

class LearningEvent(Base):
    """Append-only activity event log. Never update or delete rows."""
    __tablename__ = "learning_events"
    __table_args__ = (
        Index("ix_le_user_occurred", "user_id", "occurred_at"),
        Index("ix_le_type_occurred", "event_type", "occurred_at"),
        Index("ix_le_subject_occurred", "subject", "occurred_at"),
        Index("ix_le_user_type_occurred", "user_id", "event_type", "occurred_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    idempotency_key = Column(String(128), unique=True, nullable=True)
    event_type = Column(String(40), nullable=False)
    subject = Column(String(20), nullable=True)
    entity_type = Column(String(30), nullable=True)   # lesson / quiz / session / message
    entity_id = Column(String(64), nullable=True)     # UUID or BIGINT as string
    event_value = Column(Numeric(10, 2), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="learning_events")


# ============================================================================
# 3.4  GAMIFICATION & PROGRESS READ MODELS
# ============================================================================

class LevelDefinition(Base):
    """XP → level mapping. Seed once; drive all level-up logic from this."""
    __tablename__ = "level_definitions"

    level = Column(Integer, primary_key=True)
    xp_required = Column(Integer, nullable=False)   # total XP needed to reach this level
    label = Column(String(50), nullable=False)       # "Beginner", "Scholar", …


class DailyProgress(Base):
    """Denormalised per-day snapshot updated by stream worker / background job."""
    __tablename__ = "daily_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_user_daily_progress"),
        Index("ix_daily_progress_user_date", "user_id", "date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    study_minutes = Column(Integer, nullable=False, default=0)
    lessons_completed = Column(Integer, nullable=False, default=0)
    quizzes_taken = Column(Integer, nullable=False, default=0)
    xp_earned = Column(Integer, nullable=False, default=0)
    subjects_studied = Column(JSON, nullable=False, default=list)   # ["physics","chemistry"]

    user = relationship("User", back_populates="daily_progress_rows")


class UserGamificationSnapshot(Base):
    """One row per user — ultra-fast dashboard reads (XP, level, streak)."""
    __tablename__ = "user_gamification_snapshot"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    total_xp = Column(Integer, nullable=False, default=0)
    current_level = Column(Integer, nullable=False, default=1)
    xp_to_next_level = Column(Integer, nullable=False, default=500)
    current_streak = Column(Integer, nullable=False, default=0)
    longest_streak = Column(Integer, nullable=False, default=0)
    last_study_date = Column(Date, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="gamification_snapshot")


class BadgeDefinition(Base):
    """Catalog of all possible badges."""
    __tablename__ = "badge_definitions"

    id = Column(String(50), primary_key=True)           # slug: first_lesson, streak_7, …
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    icon = Column(String(16), nullable=False)            # emoji or icon code
    criteria = Column(JSON, nullable=False, default=dict)  # {"streak_days": 7}
    rarity = Column(String(20), nullable=True, default="common")  # common/rare/epic/legendary
    category = Column(String(30), nullable=True)         # streak/mastery/milestone/social
    available_from = Column(DateTime, nullable=True)     # time-limited badges
    available_until = Column(DateTime, nullable=True)
    global_earned_count = Column(Integer, nullable=False, default=0)

    user_badges = relationship("UserBadge", back_populates="badge")


class UserBadge(Base):
    """Junction — badges earned by a user."""
    __tablename__ = "user_badges"
    __table_args__ = (
        UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    badge_id = Column(String(50), ForeignKey("badge_definitions.id"), nullable=False)
    earned_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="badges")
    badge = relationship("BadgeDefinition", back_populates="user_badges")


# ============================================================================
# 3.5  QUIZ MODEL
# ============================================================================

class Quiz(Base):
    """Quiz session — one per attempt, UUID PK."""
    __tablename__ = "quizzes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(20), nullable=False)
    topic = Column(String(120), nullable=True)
    difficulty = Column(String(20), nullable=False)     # easy/medium/hard/mixed
    question_count = Column(Integer, nullable=False)
    time_limit_sec = Column(Integer, nullable=True)     # NULL = untimed
    status = Column(String(20), nullable=False, default="active")  # active/completed/abandoned
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="quizzes")
    questions = relationship(
        "QuizQuestion", back_populates="quiz", cascade="all, delete-orphan"
    )
    attempt_answers = relationship(
        "QuizAttemptAnswer", back_populates="quiz", cascade="all, delete-orphan"
    )
    attempt_summary = relationship(
        "QuizAttemptSummary", back_populates="quiz",
        uselist=False, cascade="all, delete-orphan"
    )


class QuizQuestion(Base):
    """Individual question within a quiz."""
    __tablename__ = "quiz_questions"
    __table_args__ = (
        UniqueConstraint("quiz_id", "question_no", name="uq_quiz_question_no"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_id = Column(String(36), ForeignKey("quizzes.id"), nullable=False, index=True)
    question_no = Column(Integer, nullable=False)   # 1-indexed
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)           # ["A","B","C","D"]
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    topic = Column(String(120), nullable=True)
    difficulty = Column(String(20), nullable=True)

    quiz = relationship("Quiz", back_populates="questions")
    answer = relationship("QuizAttemptAnswer", back_populates="question", uselist=False)


class QuizAttemptAnswer(Base):
    """User's answer to a single question in a quiz."""
    __tablename__ = "quiz_attempt_answers"
    __table_args__ = (
        UniqueConstraint("quiz_id", "question_id", name="uq_quiz_answer"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_id = Column(String(36), ForeignKey("quizzes.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("quiz_questions.id"), nullable=False)
    user_answer = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    score_awarded = Column(Integer, nullable=False, default=0)
    time_taken_sec = Column(Integer, nullable=True)
    evaluated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    quiz = relationship("Quiz", back_populates="attempt_answers")
    question = relationship("QuizQuestion", back_populates="answer")


class QuizAttemptSummary(Base):
    """Final summary row for a completed quiz (blueprint §3.5 quiz_attempts).
    Named 'quiz_attempt_summaries' to avoid conflict with legacy quiz_attempts table.
    """
    __tablename__ = "quiz_attempt_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_id = Column(String(36), ForeignKey("quizzes.id"), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(20), nullable=False)
    difficulty = Column(String(20), nullable=False)
    correct_answers = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    score_percent = Column(Numeric(5, 2), nullable=False)
    xp_awarded = Column(Integer, nullable=False)
    time_taken_sec = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    quiz = relationship("Quiz", back_populates="attempt_summary")


# ============================================================================
# 3.6  LEARN CHAT / TUTOR ANALYTICS
# ============================================================================

class LearningSession(Base):
    """Chat/study session — UUID PK."""
    __tablename__ = "learning_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(20), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    # duration_minutes: derive as (ended_at - started_at) / 60 — not stored

    user = relationship("User", back_populates="learning_sessions")
    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )
    query_events = relationship("QueryEvent", back_populates="session")


class ChatMessage(Base):
    """Individual message in a learning session."""
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_session_created", "session_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(36), ForeignKey("learning_sessions.id"), nullable=False, index=True
    )
    role = Column(String(20), nullable=False)    # user / assistant / system
    content = Column(Text, nullable=False)
    tier = Column(String(20), nullable=True)     # tier-0 / tier-1 / tier-2 / langgraph
    # use 'msg_metadata' as attribute name to avoid collision with Base.metadata
    msg_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    session = relationship("LearningSession", back_populates="messages")


class QueryEvent(Base):
    """Denormalised per-query analytics row — supports weak-topic detection."""
    __tablename__ = "query_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String(36), ForeignKey("learning_sessions.id"), nullable=True)
    query_text = Column(Text, nullable=False)
    subject = Column(String(20), nullable=True)
    intent = Column(String(50), nullable=True)
    tier = Column(String(20), nullable=True)
    confidence = Column(Numeric(5, 4), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    sources = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="query_events")
    session = relationship("LearningSession", back_populates="query_events")


# ============================================================================
# 3.7  LIBRARY
# ============================================================================

class Bookmark(Base):
    """Saved bookmark — UUID PK."""
    __tablename__ = "bookmarks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    subject = Column(String(20), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)
    path = Column(Text, nullable=True)              # deep link / route
    saved_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="bookmarks")


class StudyNote(Base):
    """User-created study note — UUID PK."""
    __tablename__ = "study_notes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    subject = Column(String(20), nullable=True)
    tags = Column(JSON, nullable=False, default=list)   # ["important","revision"]
    color = Column(String(20), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="study_notes")


# ============================================================================
# 3.8  PERSONALIZATION
# ============================================================================

class TopicMastery(Base):
    """Per-user, per-topic mastery score (0–100) and confidence."""
    __tablename__ = "topic_mastery"
    __table_args__ = (
        UniqueConstraint("user_id", "subject", "topic", name="uq_user_topic_mastery"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(20), nullable=False)
    topic = Column(String(120), nullable=False)
    mastery_score = Column(Numeric(5, 2), nullable=False, default=0)
    confidence = Column(Numeric(5, 2), nullable=False, default=0)
    last_assessed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="topic_mastery")


class LearningRecommendation(Base):
    """AI-generated recommendation for what to study next."""
    __tablename__ = "learning_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    rec_type = Column(String(40), nullable=False)       # lesson/quiz/revision/routine
    subject = Column(String(20), nullable=True)
    topic = Column(String(120), nullable=True)
    title = Column(String(255), nullable=False)
    reason = Column(Text, nullable=False)
    priority_score = Column(Numeric(6, 3), nullable=False)
    status = Column(String(20), nullable=False, default="active")  # active/accepted/dismissed/completed
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="recommendations")


class ExamReadinessSnapshot(Base):
    """Daily snapshot of projected exam performance metrics."""
    __tablename__ = "exam_readiness_snapshots"
    __table_args__ = (
        UniqueConstraint("user_id", "snapshot_date", name="uq_user_readiness_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False)
    projected_score = Column(Numeric(5, 1), nullable=True)
    syllabus_coverage_percent = Column(Numeric(5, 2), nullable=True)
    accuracy_percent = Column(Numeric(5, 2), nullable=True)
    speed_qph = Column(Numeric(6, 2), nullable=True)    # questions per hour
    consistency_score = Column(Numeric(5, 2), nullable=True)
    risk_band = Column(String(20), nullable=True)       # low / medium / high

    user = relationship("User", back_populates="readiness_snapshots")


class HabitSignal(Base):
    """Daily study habit metrics — session count, focus time, etc."""
    __tablename__ = "habit_signals"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_user_habit_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    first_activity_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, nullable=True)
    session_count = Column(Integer, nullable=False, default=0)
    deep_focus_minutes = Column(Integer, nullable=False, default=0)
    interruptions_count = Column(Integer, nullable=False, default=0)

    user = relationship("User", back_populates="habit_signals")


# ============================================================================
# LEGACY  (kept for backward compatibility with existing routes/code)
# ============================================================================

class Progress(Base):
    """Legacy lesson-completion tracking. Use LearningEvent + DailyProgress going forward."""
    __tablename__ = "progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False, index=True)
    completed = Column(Boolean, default=False)
    score = Column(Float, nullable=True)
    time_spent = Column(Integer, nullable=True)
    last_accessed = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="progress")
    lesson = relationship("Lesson", back_populates="progress")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "lesson_id": self.lesson_id,
            "completed": self.completed,
            "score": self.score,
            "time_spent": self.time_spent,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
        }


class QuizAttempt(Base):
    """Legacy standalone quiz attempt. Use Quiz/QuizAttemptSummary going forward."""
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(20), nullable=False)
    difficulty = Column(String(20), nullable=False)
    score = Column(Float, nullable=False)
    total_questions = Column(Integer, nullable=False)
    correct_answers = Column(Integer, nullable=False)
    time_taken = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="quiz_attempts")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "subject": self.subject,
            "difficulty": self.difficulty,
            "score": self.score,
            "total_questions": self.total_questions,
            "correct_answers": self.correct_answers,
            "time_taken": self.time_taken,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
