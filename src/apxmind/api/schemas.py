"""
Pydantic Request/Response Schemas
===================================

Unified request and response models for the APXMIND FastAPI application.
These replace the ad-hoc JSON parsing from the Flask controllers.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


# ============================================================================
# ENUMS
# ============================================================================

class SubjectEnum(str, Enum):
    biology = "biology"
    chemistry = "chemistry"
    physics = "physics"


class DifficultyEnum(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class IntentEnum(str, Enum):
    simple = "simple"
    retrieval = "retrieval"
    complex = "complex"
    quiz = "quiz"


# ============================================================================
# QUERY
# ============================================================================

class QueryRequest(BaseModel):
    """POST /api/query — ask a question."""
    query: str = Field(..., min_length=1, max_length=2000, description="The user's question")
    subject: Optional[SubjectEnum] = Field(None, description="Optional subject hint")
    user_id: Optional[int] = Field(None, description="Optional user ID for context")
    context: Optional[dict] = Field(default_factory=dict, description="Additional context")


class SourceInfo(BaseModel):
    content: str = ""
    metadata: dict = Field(default_factory=dict)


class QueryMetadata(BaseModel):
    tier: str = "tier1"
    agent: str = "retriever"
    intent: str = ""
    subject: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    sources: List[str] = Field(default_factory=list)
    tier0_latency_ms: float = 0.0
    tier1_latency_ms: float = 0.0
    tier2_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    timestamp: str = ""


class QueryResponse(BaseModel):
    """Response from the query endpoint."""
    success: bool = True
    answer: str = ""
    metadata: QueryMetadata = Field(default_factory=QueryMetadata)


# ============================================================================
# SUBJECTS & LESSONS
# ============================================================================

class SubjectResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    total_lessons: int = 0


class LessonResponse(BaseModel):
    id: int
    subject_id: int
    subject_name: Optional[str] = None
    title: str
    description: Optional[str] = None
    difficulty: str = "medium"
    order: int
    estimated_time: int = 30
    topics: List[str] = Field(default_factory=list)


class SubjectListResponse(BaseModel):
    success: bool = True
    data: List[SubjectResponse] = Field(default_factory=list)
    count: int = 0


class LessonListResponse(BaseModel):
    success: bool = True
    subject: Optional[SubjectResponse] = None
    lessons: List[LessonResponse] = Field(default_factory=list)
    count: int = 0


# ============================================================================
# TRAINER / QUIZ
# ============================================================================

class QuizRequest(BaseModel):
    """POST /api/trainer/generate-quiz"""
    subject: SubjectEnum
    difficulty: DifficultyEnum = DifficultyEnum.medium
    question_count: int = Field(default=5, ge=1, le=20)
    topics: List[str] = Field(default_factory=list)


class QuizQuestion(BaseModel):
    id: int
    question: str
    options: List[str]
    correct_answer: str = ""
    explanation: str = ""
    difficulty: str = "medium"
    topic: str = ""


class QuizData(BaseModel):
    quiz_id: str
    subject: str
    difficulty: str
    questions: List[QuizQuestion]
    total_questions: int
    time_limit: int  # seconds
    created_at: str = ""


class QuizResponse(BaseModel):
    success: bool = True
    quiz: Optional[QuizData] = None
    metadata: Optional[dict] = None


class AnswerSubmitRequest(BaseModel):
    """POST /api/trainer/submit-answer"""
    quiz_id: str
    question_id: int
    user_answer: str
    question_text: Optional[str] = None
    correct_answer: Optional[str] = None


class AnswerEvaluation(BaseModel):
    correct: bool
    correct_answer: str = ""
    explanation: str = ""


class AnswerSubmitResponse(BaseModel):
    success: bool = True
    evaluation: Optional[AnswerEvaluation] = None


# ============================================================================
# AUTH
# ============================================================================


class OfflineProfileRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    username: Optional[str] = Field(None, min_length=1, max_length=50)
    password: str = Field(..., min_length=4)
    email: Optional[str] = Field(None, max_length=120)
    dob: Optional[str] = None
    current_class: Optional[str] = "12th"
    attempt_number: Optional[int] = 1
    target_year: Optional[str] = None
    target_score: Optional[int] = 650
    strong_subjects: List[str] = Field(default_factory=list)
    weak_subjects: List[str] = Field(default_factory=list)
    daily_study_target: Optional[int] = 4
    daily_study_target_hours: Optional[float] = None
    preferred_language: Optional[str] = "english"
    learning_level: Optional[str] = "beginner"
    timezone: Optional[str] = "Asia/Kolkata"


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    username: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[str] = Field(None, max_length=120)
    avatar_url: Optional[str] = None
    dob: Optional[str] = None
    current_class: Optional[str] = None
    attempt_number: Optional[int] = None
    target_year: Optional[str] = None
    target_score: Optional[int] = None
    strong_subjects: Optional[List[str]] = None
    weak_subjects: Optional[List[str]] = None
    daily_study_target: Optional[int] = None
    daily_study_target_hours: Optional[float] = None
    preferred_language: Optional[str] = None
    learning_level: Optional[str] = None
    timezone: Optional[str] = None

class RegisterRequest(BaseModel):
    email: str = Field(None, min_length=5, max_length=120)
    name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=4)


class LoginRequest(BaseModel):
    name: Optional[str] = None      # login by display name
    username: Optional[str] = None  # login by username
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    name: str
    username: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    dob: Optional[str] = None
    current_class: Optional[str] = None
    attempt_number: Optional[int] = None
    target_year: Optional[str] = None
    target_score: Optional[int] = None
    strong_subjects: List[str] = Field(default_factory=list)
    weak_subjects: List[str] = Field(default_factory=list)
    daily_study_target: Optional[int] = None
    daily_study_target_hours: Optional[float] = None
    preferred_language: Optional[str] = None
    learning_level: str = "beginner"
    timezone: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AuthResponse(BaseModel):
    success: bool = True
    token: str = ""
    user: Optional[UserResponse] = None


# ============================================================================
# HEALTH / INFO
# ============================================================================

class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: str = ""
    components: dict = Field(default_factory=dict)
    version: str = "2.0.0"


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    message: Optional[str] = None
    status: int = 500
    timestamp: str = ""


class LocalUserDropdown(BaseModel):
    id: int
    name: str

class LocalDropdownResponse(BaseModel):
    success: bool = True
    users: List[LocalUserDropdown]


# ============================================================================
# DASHBOARD & PROGRESS
# ============================================================================

class DailyProgressResponse(BaseModel):
    date: str
    study_minutes: int = 0
    lessons_completed: int = 0
    quizzes_taken: int = 0
    xp_earned: int = 0
    subjects_studied: List[str] = Field(default_factory=list)


class GamificationSnapshotResponse(BaseModel):
    user_id: int
    total_xp: int = 0
    current_level: int = 1
    level_label: Optional[str] = None
    xp_to_next_level: int = 500
    current_streak: int = 0
    longest_streak: int = 0
    last_study_date: Optional[str] = None


class DashboardSummaryResponse(BaseModel):
    success: bool = True
    gamification: GamificationSnapshotResponse
    today: DailyProgressResponse
    badges_count: int = 0


class RecordStudyMinutesRequest(BaseModel):
    minutes: int = Field(..., ge=1, le=720)
    subject: SubjectEnum
    date: Optional[str] = None   # ISO date YYYY-MM-DD; defaults to today


class DailyProgressListResponse(BaseModel):
    success: bool = True
    days: List[DailyProgressResponse] = Field(default_factory=list)


# ============================================================================
# QUIZ V2  (DB-persisted, blueprint §3.5)
# ============================================================================

class StartQuizRequest(BaseModel):
    subject: SubjectEnum
    difficulty: str = Field(default="medium", pattern=r"^(easy|medium|hard|mixed)$")
    question_count: int = Field(default=5, ge=1, le=20)
    time_limit_sec: Optional[int] = Field(None, ge=30, le=7200)
    topic: Optional[str] = Field(None, max_length=120)


class QuizQuestionOut(BaseModel):
    """Question returned to client — correct_answer intentionally omitted."""
    id: int
    question_no: int
    question_text: str
    options: List[str]
    topic: Optional[str] = None
    difficulty: Optional[str] = None


class QuizMetaOut(BaseModel):
    id: str
    subject: str
    topic: Optional[str] = None
    difficulty: str
    question_count: int
    time_limit_sec: Optional[int] = None
    status: str
    started_at: str
    completed_at: Optional[str] = None


class StartQuizResponse(BaseModel):
    success: bool = True
    quiz: QuizMetaOut
    questions: List[QuizQuestionOut]


class SubmitAnswerRequest(BaseModel):
    question_id: int
    user_answer: str = Field(..., min_length=1)


class SubmitAnswerOut(BaseModel):
    is_correct: bool
    correct_answer: str
    explanation: Optional[str] = None
    score_awarded: int = 0


class SubmitAnswerResponse(BaseModel):
    success: bool = True
    result: SubmitAnswerOut


class UpdateAnswerRequest(BaseModel):
    user_answer: str = Field(..., min_length=1)


class QuizResultQuestion(BaseModel):
    question_no: int
    question_text: str
    options: List[str]
    correct_answer: str
    user_answer: Optional[str] = None
    is_correct: Optional[bool] = None
    explanation: Optional[str] = None


class QuizSummaryOut(BaseModel):
    id: int
    quiz_id: str
    subject: str
    difficulty: str
    correct_answers: int
    total_questions: int
    score_percent: float
    xp_awarded: int
    time_taken_sec: Optional[int] = None
    created_at: str


class QuizResultsResponse(BaseModel):
    success: bool = True
    quiz: QuizMetaOut
    questions: List[QuizResultQuestion]
    summary: Optional[QuizSummaryOut] = None


class FinishQuizResponse(BaseModel):
    success: bool = True
    summary: QuizSummaryOut


class QuizListResponse(BaseModel):
    success: bool = True
    quizzes: List[QuizMetaOut] = Field(default_factory=list)
    total: int = 0


# ============================================================================
# LEARN SESSIONS & CHAT  (blueprint §3.6)
# ============================================================================

class StartSessionRequest(BaseModel):
    subject: SubjectEnum
    lesson_id: Optional[int] = None


class SessionOut(BaseModel):
    id: str
    subject: str
    lesson_id: Optional[int] = None
    started_at: str
    ended_at: Optional[str] = None
    duration_minutes: Optional[float] = None


class SessionListResponse(BaseModel):
    success: bool = True
    sessions: List[SessionOut] = Field(default_factory=list)
    total: int = 0


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class MessageOut(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    tier: Optional[str] = None
    created_at: str


class MessageListResponse(BaseModel):
    success: bool = True
    messages: List[MessageOut] = Field(default_factory=list)
    total: int = 0


# ============================================================================
# LIBRARY — BOOKMARKS  (blueprint §3.7)
# ============================================================================

class CreateBookmarkRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    subject: SubjectEnum
    lesson_id: Optional[int] = None
    path: Optional[str] = None


class UpdateBookmarkRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    subject: Optional[SubjectEnum] = None
    lesson_id: Optional[int] = None
    path: Optional[str] = None


class BookmarkOut(BaseModel):
    id: str
    title: str
    subject: str
    lesson_id: Optional[int] = None
    path: Optional[str] = None
    saved_at: str
    updated_at: str


class BookmarkListResponse(BaseModel):
    success: bool = True
    bookmarks: List[BookmarkOut] = Field(default_factory=list)
    total: int = 0


# ============================================================================
# LIBRARY — STUDY NOTES  (blueprint §3.7)
# ============================================================================

class CreateNoteRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    subject: Optional[SubjectEnum] = None
    tags: List[str] = Field(default_factory=list)
    color: Optional[str] = Field(None, max_length=20)


class UpdateNoteRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    subject: Optional[SubjectEnum] = None
    tags: Optional[List[str]] = None
    color: Optional[str] = Field(None, max_length=20)


class NoteOut(BaseModel):
    id: str
    title: str
    content: str
    subject: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    color: Optional[str] = None
    created_at: str
    updated_at: str


class NoteListResponse(BaseModel):
    success: bool = True
    notes: List[NoteOut] = Field(default_factory=list)
    total: int = 0


# ============================================================================
# ACHIEVEMENTS  (blueprint §3.4)
# ============================================================================

class BadgeOut(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    criteria: dict = Field(default_factory=dict)
    earned: bool = False
    earned_at: Optional[str] = None


class AchievementsResponse(BaseModel):
    success: bool = True
    badges: List[BadgeOut] = Field(default_factory=list)
    earned_count: int = 0
    total_count: int = 0


# ============================================================================
# SUBJECT PREFERENCES  (blueprint §3.1)
# ============================================================================

class SubjectPreferenceRequest(BaseModel):
    strength: str = Field(..., pattern=r"^(strong|weak|neutral)$")
    priority_rank: Optional[int] = Field(None, ge=1, le=3)


class SubjectPreferenceOut(BaseModel):
    subject: str
    strength: str
    priority_rank: Optional[int] = None


class SubjectPreferencesResponse(BaseModel):
    success: bool = True
    preferences: List[SubjectPreferenceOut] = Field(default_factory=list)


# ============================================================================
# INSIGHTS — TOPIC MASTERY  (blueprint §4.x)
# ============================================================================

class TopicMasteryOut(BaseModel):
    subject: str
    topic: str
    mastery_score: float = 0.0
    confidence: float = 0.0
    last_assessed_at: Optional[str] = None


class TopicMasteryListResponse(BaseModel):
    success: bool = True
    mastery: List[TopicMasteryOut] = Field(default_factory=list)
    total: int = 0


# ============================================================================
# INSIGHTS — RECOMMENDATIONS
# ============================================================================

class RecommendationOut(BaseModel):
    id: int
    rec_type: str
    subject: Optional[str] = None
    topic: Optional[str] = None
    title: str
    reason: str
    priority_score: float = 0.0
    status: str = "active"
    generated_at: str
    expires_at: Optional[str] = None


class RecommendationsListResponse(BaseModel):
    success: bool = True
    recommendations: List[RecommendationOut] = Field(default_factory=list)
    total: int = 0


class UpdateRecommendationRequest(BaseModel):
    status: str = Field(..., pattern=r"^(accepted|dismissed|completed)$")


# ============================================================================
# INSIGHTS — EXAM READINESS + HABITS
# ============================================================================

class ExamReadinessOut(BaseModel):
    snapshot_date: str
    projected_score: Optional[float] = None
    syllabus_coverage_percent: Optional[float] = None
    accuracy_percent: Optional[float] = None
    speed_qph: Optional[float] = None
    consistency_score: Optional[float] = None
    risk_band: Optional[str] = None


class ExamReadinessListResponse(BaseModel):
    success: bool = True
    latest: Optional[ExamReadinessOut] = None
    history: List[ExamReadinessOut] = Field(default_factory=list)


class HabitSignalOut(BaseModel):
    date: str
    session_count: int = 0
    deep_focus_minutes: int = 0
    interruptions_count: int = 0
    first_activity_at: Optional[str] = None
    last_activity_at: Optional[str] = None


class HabitSignalsResponse(BaseModel):
    success: bool = True
    signals: List[HabitSignalOut] = Field(default_factory=list)
