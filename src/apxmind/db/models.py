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

    # Security columns (Phase 1)
    password_changed_at = Column(DateTime, nullable=True)
    must_change_password = Column(Boolean, default=False)
    recovery_email = Column(String(120), nullable=True)
    recovery_phone = Column(String(20), nullable=True)
    security_questions = Column(JSON, nullable=True)
    terms_accepted_at = Column(DateTime, nullable=True)
    privacy_accepted_at = Column(DateTime, nullable=True)
    gdpr_consent_at = Column(DateTime, nullable=True)
    marketing_consent = Column(Boolean, default=False)
    data_export_requested_at = Column(DateTime, nullable=True)
    account_deletion_requested_at = Column(DateTime, nullable=True)

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
    spaced_reviews = relationship(
        "SpacedReview", back_populates="user", cascade="all, delete-orphan"
    )
    mistake_cards = relationship(
        "MistakeCard", back_populates="user", cascade="all, delete-orphan"
    )
    planner_tasks = relationship(
        "PlannerTask", back_populates="user", cascade="all, delete-orphan"
    )
    sync_journal_rows = relationship(
        "SyncJournal", back_populates="user", cascade="all, delete-orphan"
    )

    # Relationships — legacy tables
    progress = relationship("Progress", back_populates="user", cascade="all, delete-orphan")
    quiz_attempts = relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")

    # Relationships — Security (Phase 1)
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    login_history = relationship("LoginHistory", back_populates="user", cascade="all, delete-orphan")
    email_verification_tokens = relationship("EmailVerificationToken", back_populates="user", cascade="all, delete-orphan")
    two_factor_backup_codes = relationship("TwoFactorBackupCode", back_populates="user", cascade="all, delete-orphan")
    devices = relationship("UserDevice", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    security_events = relationship("SecurityEvent", back_populates="user", cascade="all, delete-orphan")

    # Relationships — Notifications (Phase 3)
    notifications = relationship("UserNotification", back_populates="user", cascade="all, delete-orphan")
    push_tokens = relationship("PushToken", back_populates="user", cascade="all, delete-orphan")
    notification_preferences = relationship("NotificationPreference", back_populates="user", cascade="all, delete-orphan")
    notification_settings = relationship("NotificationSetting", back_populates="user", uselist=False, cascade="all, delete-orphan")
    study_reminders = relationship("StudyReminder", back_populates="user", cascade="all, delete-orphan")

    # Relationships — Support and moderation (Phase 4)
    support_tickets = relationship("SupportTicket", back_populates="user", cascade="all, delete-orphan")
    content_reports = relationship("ContentReport", back_populates="reporter", cascade="all, delete-orphan")
    warnings = relationship("UserWarning", back_populates="user", cascade="all, delete-orphan")
    bans = relationship("UserBan", back_populates="user", cascade="all, delete-orphan")
    feature_flag_overrides = relationship("FeatureFlagOverride", back_populates="user", cascade="all, delete-orphan")
    announcement_dismissals = relationship("AnnouncementDismissal", back_populates="user", cascade="all, delete-orphan")

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


class SpacedReview(Base):
    """Offline-first spaced repetition queue item."""
    __tablename__ = "spaced_reviews"
    __table_args__ = (
        UniqueConstraint("user_id", "source_type", "source_id", name="uq_spaced_review_source"),
        Index("ix_spaced_reviews_user_due", "user_id", "due_at"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    topic = Column(String(160), nullable=False)
    subject = Column(String(20), nullable=True)
    source_type = Column(String(40), nullable=False)  # lesson_recall / mistake_card / flashcard
    source_id = Column(String(80), nullable=False)
    interval_step = Column(Integer, nullable=False, default=1)
    due_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_reviewed_at = Column(DateTime, nullable=True)
    last_result = Column(String(20), nullable=True)  # correct / partial / incorrect
    ease_factor = Column(Numeric(4, 2), nullable=False, default=2.50)
    streak = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="spaced_reviews")


class MistakeCard(Base):
    """Structured error notebook row for repeated-mistake reduction."""
    __tablename__ = "mistake_cards"
    __table_args__ = (
        Index("ix_mistake_cards_user_due", "user_id", "next_due_at"),
        Index("ix_mistake_cards_user_subject_topic", "user_id", "subject", "topic"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(20), nullable=True)
    topic = Column(String(160), nullable=True)
    source_type = Column(String(40), nullable=True)  # quiz / recall / drill
    source_id = Column(String(80), nullable=True)
    error_reason_code = Column(String(40), nullable=False, default="other")
    prompt_snapshot = Column(Text, nullable=False)
    correct_explanation = Column(Text, nullable=True)
    times_seen = Column(Integer, nullable=False, default=1)
    times_repeated = Column(Integer, nullable=False, default=0)
    last_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    next_due_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="mistake_cards")


class PlannerTask(Base):
    """Daily adaptive planner task with execution status."""
    __tablename__ = "planner_tasks"
    __table_args__ = (
        Index("ix_planner_tasks_user_date", "user_id", "task_date"),
        Index("ix_planner_tasks_user_status_date", "user_id", "status", "task_date"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    task_date = Column(Date, nullable=False)
    task_type = Column(String(30), nullable=False)  # revision / new_learning / mini_set / stamina
    subject = Column(String(20), nullable=True)
    topic = Column(String(160), nullable=True)
    recommended_minutes = Column(Integer, nullable=False, default=15)
    priority_score = Column(Numeric(6, 3), nullable=False, default=0)
    status = Column(String(20), nullable=False, default="pending")  # pending / completed / skipped
    completed_at = Column(DateTime, nullable=True)
    source_recommendation_id = Column(Integer, ForeignKey("learning_recommendations.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="planner_tasks")


class ExamStaminaSession(Base):
    """Timed stamina drill session with block plan and performance summary."""
    __tablename__ = "exam_stamina_sessions"
    __table_args__ = (
        Index("ix_exam_stamina_sessions_user_started", "user_id", "started_at"),
        Index("ix_exam_stamina_sessions_user_status", "user_id", "status"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    mode = Column(String(20), nullable=False, default="mixed")
    subject = Column(String(20), nullable=True)
    topic = Column(String(160), nullable=True)
    planned_duration_minutes = Column(Integer, nullable=False, default=30)
    planned_questions = Column(Integer, nullable=False, default=30)
    block_count = Column(Integer, nullable=False, default=3)
    block_plan = Column(JSON, nullable=True)
    performance_summary = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="active")  # active / completed / abandoned
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class SyncJournal(Base):
    """Reliable local-first sync journal mirror with idempotency tracking."""
    __tablename__ = "sync_journal"
    __table_args__ = (
        Index("ix_sync_journal_user_status_created", "user_id", "status", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    operation_type = Column(String(20), nullable=False)  # create / update / delete / event
    entity_type = Column(String(40), nullable=False)
    entity_id = Column(String(80), nullable=True)
    payload = Column(JSON, nullable=True)
    idempotency_key = Column(String(160), nullable=False, unique=True, index=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(DateTime, nullable=True)
    synced_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="pending")  # pending / synced / failed
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="sync_journal_rows")


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


# ============================================================================
# PHASE 1: SECURITY & AUTHENTICATION  (10 MODELS)
# ============================================================================

class PasswordResetToken(Base):
    """Password reset tokens with expiration."""
    __tablename__ = "password_reset_tokens"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(256), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45), nullable=True)
    user = relationship("User", back_populates="password_reset_tokens")


class RefreshToken(Base):
    """JWT refresh tokens for session management."""
    __tablename__ = "refresh_tokens"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(36), ForeignKey("user_sessions.id", ondelete="SET NULL"), nullable=True)
    token_hash = Column(String(256), unique=True, nullable=False, index=True)
    device_fingerprint = Column(String(256), nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True)
    revoke_reason = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="refresh_tokens")
    session = relationship("UserSession", back_populates="refresh_tokens")


class RateLimit(Base):
    """API rate limiting records."""
    __tablename__ = "rate_limits"
    __table_args__ = (Index("ix_rate_limit_lookup", "identifier", "endpoint", "window_end"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(256), nullable=False)
    identifier_type = Column(String(20), nullable=False)
    endpoint = Column(String(255), nullable=False)
    request_count = Column(Integer, default=1)
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)


class SecurityBlock(Base):
    """Blocked IPs, users, or devices."""
    __tablename__ = "security_blocks"
    __table_args__ = (Index("ix_block_lookup", "block_type", "identifier", "is_active"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    block_type = Column(String(20), nullable=False)
    identifier = Column(String(256), nullable=False)
    reason = Column(Text, nullable=False)
    severity = Column(String(20), default="medium")
    blocked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    blocked_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)


class LoginHistory(Base):
    """Login attempt history for security monitoring."""
    __tablename__ = "login_history"
    __table_args__ = (Index("ix_login_user_time", "user_id", "created_at"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(50), nullable=True)
    ip_address = Column(String(45), nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    device_type = Column(String(30), nullable=True)
    browser = Column(String(50), nullable=True)
    browser_version = Column(String(20), nullable=True)
    os = Column(String(50), nullable=True)
    os_version = Column(String(20), nullable=True)
    location_country = Column(String(50), nullable=True)
    location_state = Column(String(100), nullable=True)
    location_city = Column(String(100), nullable=True)
    is_suspicious = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="login_history")


class EmailVerificationToken(Base):
    """Email verification tokens."""
    __tablename__ = "email_verification_tokens"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(120), nullable=False)
    token_hash = Column(String(256), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="email_verification_tokens")


class TwoFactorBackupCode(Base):
    """2FA emergency recovery codes."""
    __tablename__ = "two_factor_backup_codes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    code_hash = Column(String(256), nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="two_factor_backup_codes")


class UserDevice(Base):
    """Trusted devices for a user."""
    __tablename__ = "user_devices"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_name = Column(String(100), nullable=True)
    device_fingerprint = Column(String(256), nullable=True, index=True)
    device_type = Column(String(30), nullable=False)
    platform = Column(String(30), nullable=True)
    os = Column(String(50), nullable=True)
    browser = Column(String(50), nullable=True)
    is_trusted = Column(Boolean, default=False)
    last_active_at = Column(DateTime, nullable=True)
    last_ip_address = Column(String(45), nullable=True)
    last_location = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="devices")


class UserSession(Base):
    """User sessions for multi-device management."""
    __tablename__ = "user_sessions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String(36), ForeignKey("user_devices.id"), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    location = Column(String(100), nullable=True)
    is_revoked = Column(Boolean, default=False, index=True)
    revoked_at = Column(DateTime, nullable=True)
    revoke_reason = Column(String(50), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="sessions")
    device = relationship("UserDevice")
    refresh_tokens = relationship("RefreshToken", back_populates="session")


class SecurityEvent(Base):
    """Detailed security event audit log."""
    __tablename__ = "security_events"
    __table_args__ = (Index("ix_security_event_user", "user_id", "created_at"),)
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    description = Column(Text, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    device_id = Column(String(36), nullable=True)
    event_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="security_events")


# ============================================================================
# PHASE 3: NOTIFICATIONS  (10 MODELS)
# ============================================================================

class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    title_template = Column(Text, nullable=False)
    body_template = Column(Text, nullable=False)
    image_url = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    color = Column(String(20), nullable=True)
    channels = Column(JSON, nullable=False, default=list)
    email_subject_template = Column(Text, nullable=True)
    email_html_template = Column(Text, nullable=True)
    sms_template = Column(Text, nullable=True)
    variables = Column(JSON, nullable=True)
    is_transactional = Column(Boolean, default=False)
    priority = Column(String(10), default="normal")
    ttl_hours = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    notifications = relationship("UserNotification", back_populates="template")
    scheduled_notifications = relationship("ScheduledNotification", back_populates="template")


class UserNotification(Base):
    __tablename__ = "user_notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id = Column(String(50), ForeignKey("notification_templates.id"), nullable=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    image_url = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    category = Column(String(50), nullable=False)
    subcategory = Column(String(50), nullable=True)
    action_type = Column(String(30), nullable=True)
    action_data = Column(JSON, nullable=True)
    priority = Column(String(10), default="normal")
    group_key = Column(String(50), nullable=True)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    is_seen = Column(Boolean, default=False)
    seen_at = Column(DateTime, nullable=True)
    is_dismissed = Column(Boolean, default=False)
    dismissed_at = Column(DateTime, nullable=True)
    delivered_via = Column(JSON, default=list)
    delivery_errors = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    scheduled_for = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="notifications")
    template = relationship("NotificationTemplate", back_populates="notifications")
    delivery_logs = relationship("NotificationDeliveryLog", back_populates="notification", cascade="all, delete-orphan")


class PushToken(Base):
    __tablename__ = "push_tokens"
    __table_args__ = (
        UniqueConstraint("user_id", "token", name="uq_push_user_token"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(512), nullable=False, index=True)
    token_type = Column(String(20), nullable=False)
    device_id = Column(String(100), nullable=True)
    device_name = Column(String(100), nullable=True)
    platform = Column(String(20), nullable=False)
    app_version = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    failed_count = Column(Integer, default=0)
    last_failure_at = Column(DateTime, nullable=True)
    last_failure_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="push_tokens")


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "category", name="uq_notif_pref_user_category"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    in_app = Column(Boolean, default=True)
    push = Column(Boolean, default=True)
    email = Column(Boolean, default=False)
    sms = Column(Boolean, default=False)
    max_per_day = Column(Integer, nullable=True)
    digest_mode = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="notification_preferences")


class NotificationSetting(Base):
    __tablename__ = "notification_settings"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    all_notifications_enabled = Column(Boolean, default=True)
    push_enabled = Column(Boolean, default=True)
    email_enabled = Column(Boolean, default=True)
    sms_enabled = Column(Boolean, default=False)
    quiet_hours_enabled = Column(Boolean, default=False)
    quiet_hours_start = Column(String(8), nullable=True)
    quiet_hours_end = Column(String(8), nullable=True)
    quiet_hours_timezone = Column(String(64), default="Asia/Kolkata")
    email_digest_enabled = Column(Boolean, default=True)
    email_digest_frequency = Column(String(20), default="daily")
    email_digest_time = Column(String(8), default="09:00")
    preferred_language = Column(String(10), default="en")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="notification_settings")


class ScheduledNotification(Base):
    __tablename__ = "scheduled_notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    segment_id = Column(Integer, nullable=True)
    template_id = Column(String(50), ForeignKey("notification_templates.id"), nullable=True)
    title = Column(String(255), nullable=True)
    body = Column(Text, nullable=True)
    variables = Column(JSON, nullable=True)
    scheduled_for = Column(DateTime, nullable=False, index=True)
    timezone = Column(String(64), default="Asia/Kolkata")
    is_recurring = Column(Boolean, default=False)
    recurrence_rule = Column(String(100), nullable=True)
    recurrence_end_date = Column(Date, nullable=True)
    last_sent_at = Column(DateTime, nullable=True)
    next_occurrence = Column(DateTime, nullable=True)
    status = Column(String(20), default="pending", index=True)
    sent_at = Column(DateTime, nullable=True)
    failure_reason = Column(Text, nullable=True)
    campaign_name = Column(String(100), nullable=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    template = relationship("NotificationTemplate", back_populates="scheduled_notifications")


class NotificationDeliveryLog(Base):
    __tablename__ = "notification_delivery_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    notification_id = Column(String(36), ForeignKey("user_notifications.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, index=True)
    provider = Column(String(30), nullable=True)
    provider_message_id = Column(String(255), nullable=True)
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    notification = relationship("UserNotification", back_populates="delivery_logs")


class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    subject_template = Column(Text, nullable=False)
    html_template = Column(Text, nullable=False)
    text_template = Column(Text, nullable=True)
    from_name = Column(String(100), default="ApxMind")
    from_email = Column(String(120), default="noreply@apxmind.com")
    reply_to = Column(String(120), nullable=True)
    variables = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EmailLog(Base):
    __tablename__ = "email_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    template_id = Column(String(50), ForeignKey("email_templates.id"), nullable=True)
    to_email = Column(String(120), nullable=False)
    subject = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False, index=True)
    provider = Column(String(30), default="sendgrid")
    provider_message_id = Column(String(255), nullable=True)
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    bounced_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class StudyReminder(Base):
    __tablename__ = "study_reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    reminder_time = Column(String(8), nullable=False)
    days_of_week = Column(JSON, nullable=False, default=list)
    timezone = Column(String(64), default="Asia/Kolkata")
    message = Column(Text, nullable=True)
    target_type = Column(String(30), nullable=True)
    target_subject = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    last_sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="study_reminders")


# ============================================================================
# PHASE 4: SUPPORT, MODERATION, OPS  (student-facing + internal tracking)
# ============================================================================


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_number = Column(String(20), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    email = Column(String(120), nullable=False)
    name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, index=True)
    subcategory = Column(String(50), nullable=True)
    priority = Column(String(20), default="normal")
    status = Column(String(20), default="open", index=True)
    assigned_to = Column(Integer, nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    escalated_to = Column(Integer, nullable=True)
    escalated_at = Column(DateTime, nullable=True)
    first_response_at = Column(DateTime, nullable=True)
    first_response_sla_met = Column(Boolean, nullable=True)
    resolution_sla_hours = Column(Integer, default=24)
    resolution_sla_met = Column(Boolean, nullable=True)
    resolution_summary = Column(Text, nullable=True)
    resolution_type = Column(String(30), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, nullable=True)
    satisfaction_rating = Column(Integer, nullable=True)
    satisfaction_comment = Column(Text, nullable=True)
    source = Column(String(30), default="app")
    browser = Column(String(50), nullable=True)
    os = Column(String(50), nullable=True)
    app_version = Column(String(20), nullable=True)
    attachments = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="support_tickets")
    responses = relationship("TicketResponse", back_populates="ticket", cascade="all, delete-orphan")


class TicketResponse(Base):
    __tablename__ = "ticket_responses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    responder_type = Column(String(20), nullable=False)
    responder_id = Column(Integer, nullable=True)
    responder_name = Column(String(100), nullable=True)
    message = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)
    attachments = Column(JSON, nullable=True)
    is_automated = Column(Boolean, default=False)
    automation_type = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("SupportTicket", back_populates="responses")


class CannedResponse(Base):
    __tablename__ = "canned_responses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), nullable=True)
    tags = Column(JSON, nullable=True)
    usage_count = Column(Integer, default=0)
    created_by = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ContentReport(Base):
    __tablename__ = "content_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content_type = Column(String(30), nullable=False, index=True)
    content_id = Column(String(64), nullable=False, index=True)
    content_preview = Column(Text, nullable=True)
    reason = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="pending", index=True)
    reviewed_by = Column(Integer, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    action_taken = Column(String(50), nullable=True)
    action_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    reporter = relationship("User", back_populates="content_reports")


class UserWarning(Base):
    __tablename__ = "user_warnings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    warning_type = Column(String(30), nullable=False)
    severity = Column(String(20), nullable=False)
    reason = Column(Text, nullable=False)
    related_content_type = Column(String(30), nullable=True)
    related_content_id = Column(String(64), nullable=True)
    report_id = Column(Integer, ForeignKey("content_reports.id"), nullable=True)
    issued_by = Column(Integer, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="warnings")


class UserBan(Base):
    __tablename__ = "user_bans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ban_type = Column(String(30), nullable=False)
    reason = Column(Text, nullable=False)
    feature_restricted = Column(String(50), nullable=True)
    starts_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ends_at = Column(DateTime, nullable=True)
    warning_count_at_ban = Column(Integer, nullable=True)
    report_id = Column(Integer, ForeignKey("content_reports.id"), nullable=True)
    issued_by = Column(Integer, nullable=True)
    appeal_text = Column(Text, nullable=True)
    appeal_status = Column(String(20), nullable=True)
    appeal_reviewed_by = Column(Integer, nullable=True)
    appeal_reviewed_at = Column(DateTime, nullable=True)
    appeal_notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    lifted_at = Column(DateTime, nullable=True)
    lifted_by = Column(Integer, nullable=True)
    lift_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="bans")


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=False, index=True)
    rollout_percentage = Column(Integer, default=0)
    rollout_strategy = Column(String(30), nullable=True)
    target_user_ids = Column(JSON, nullable=True)
    target_segments = Column(JSON, nullable=True)
    exclude_user_ids = Column(JSON, nullable=True)
    enable_at = Column(DateTime, nullable=True)
    disable_at = Column(DateTime, nullable=True)
    has_variants = Column(Boolean, default=False)
    variants = Column(JSON, nullable=True)
    owner = Column(String(100), nullable=True)
    jira_ticket = Column(String(50), nullable=True)
    updated_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    overrides = relationship("FeatureFlagOverride", back_populates="feature", cascade="all, delete-orphan")


class FeatureFlagOverride(Base):
    __tablename__ = "feature_flag_overrides"

    feature_id = Column(Integer, ForeignKey("feature_flags.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    is_enabled = Column(Boolean, nullable=False)
    variant = Column(String(50), nullable=True)
    reason = Column(Text, nullable=True)
    set_by = Column(Integer, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    feature = relationship("FeatureFlag", back_populates="overrides")
    user = relationship("User", back_populates="feature_flag_overrides")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True)
    value = Column(JSON, nullable=False)
    value_type = Column(String(20), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)
    is_sensitive = Column(Boolean, default=False)
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(20), default="text")
    announcement_type = Column(String(30), nullable=False)
    display_location = Column(String(30), nullable=True)
    priority = Column(Integer, default=0)
    target_all = Column(Boolean, default=True)
    target_segments = Column(JSON, nullable=True)
    target_platforms = Column(JSON, nullable=True)
    starts_at = Column(DateTime, nullable=False)
    ends_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    is_dismissible = Column(Boolean, default=True)
    view_count = Column(Integer, default=0)
    dismiss_count = Column(Integer, default=0)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    dismissals = relationship("AnnouncementDismissal", back_populates="announcement", cascade="all, delete-orphan")


class AnnouncementDismissal(Base):
    __tablename__ = "announcement_dismissals"

    announcement_id = Column(Integer, ForeignKey("announcements.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    dismissed_at = Column(DateTime, default=datetime.utcnow)

    announcement = relationship("Announcement", back_populates="dismissals")
    user = relationship("User", back_populates="announcement_dismissals")
