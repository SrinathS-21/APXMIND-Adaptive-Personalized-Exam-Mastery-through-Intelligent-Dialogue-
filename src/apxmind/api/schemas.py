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
    options: Optional[List[str]] = None
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


class NextBestActionOut(BaseModel):
    key: str
    title: str
    description: str
    cta_label: str
    cta_route: str
    accent: str = "accent"
    action_kind: str = "general"
    priority: int = 0
    metric_label: Optional[str] = None
    metric_value: Optional[str] = None


class NextBestActionsResponse(BaseModel):
    success: bool = True
    generated_at: str
    actions: List[NextBestActionOut] = Field(default_factory=list)


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
    confidence_level: Optional[int] = Field(default=None, ge=1, le=5)


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
    confidence_level: Optional[int] = Field(default=None, ge=1, le=5)


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
    state_label: str = "Not Started"
    last_assessed_at: Optional[str] = None


class TopicMasteryListResponse(BaseModel):
    success: bool = True
    mastery: List[TopicMasteryOut] = Field(default_factory=list)
    total: int = 0


class TopicRiskOut(BaseModel):
    subject: str
    topic: str
    mastery_score: float = 0.0
    confidence: float = 0.0
    state_label: str = "Not Started"
    repeated_mistakes: int = 0
    days_since_last_assessed: int = 0
    risk_score: float = 0.0


class TopicRiskListResponse(BaseModel):
    success: bool = True
    risk_topics: List[TopicRiskOut] = Field(default_factory=list)
    total: int = 0


class CalibrationTrendPointOut(BaseModel):
    date: str
    mean_confidence: float = 0.0
    accuracy_percent: float = 0.0
    confidence_accuracy_gap: float = 0.0
    sample_count: int = 0


class CalibrationInsightsResponse(BaseModel):
    success: bool = True
    days: int
    sample_count: int = 0
    mean_confidence: float = 0.0
    accuracy_percent: float = 0.0
    confidence_accuracy_gap: float = 0.0
    confident_wrong_rate: float = 0.0
    trend: List[CalibrationTrendPointOut] = Field(default_factory=list)


class TrendPointOut(BaseModel):
    date: str
    value: float


class WeeklyReportSummaryOut(BaseModel):
    retention_score: float = 0.0
    accuracy_percent: float = 0.0
    speed_qph: float = 0.0
    consistency_score: float = 0.0
    active_days: int = 0
    period_days: int = 7


class WeeklyReportExportOut(BaseModel):
    format: str = "json"
    content: str


class WeeklyReportResponse(BaseModel):
    success: bool = True
    start_date: str
    end_date: str
    summary: WeeklyReportSummaryOut
    retention_trend: List[TrendPointOut] = Field(default_factory=list)
    accuracy_trend: List[TrendPointOut] = Field(default_factory=list)
    speed_trend: List[TrendPointOut] = Field(default_factory=list)
    risk_topics: List[TopicRiskOut] = Field(default_factory=list)
    export: WeeklyReportExportOut


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


# ============================================================================
# RETRIEVAL / SPACED REVISION
# ============================================================================

class LessonRecallRequest(BaseModel):
    lesson_id: Optional[int] = None
    subject: Optional[SubjectEnum] = None
    topic: str = Field(..., min_length=1, max_length=160)
    response_text: str = Field(..., min_length=1, max_length=4000)
    self_score: int = Field(..., ge=0, le=100)
    time_taken_sec: Optional[int] = Field(default=None, ge=1, le=7200)


class LessonRecallResponse(BaseModel):
    success: bool = True
    score_band: str
    next_review_due: str
    spaced_review_id: str
    gaps: List[str] = Field(default_factory=list)


class SpacedReviewItemOut(BaseModel):
    id: str
    topic: str
    subject: Optional[str] = None
    source_type: str
    source_id: str
    interval_step: int
    due_at: str
    last_result: Optional[str] = None
    streak: int = 0


class SpacedQueueResponse(BaseModel):
    success: bool = True
    due_items: List[SpacedReviewItemOut] = Field(default_factory=list)
    total: int = 0


class CompleteSpacedReviewRequest(BaseModel):
    result: str = Field(..., pattern=r"^(correct|partial|incorrect)$")
    confidence_level: Optional[int] = Field(default=None, ge=1, le=5)


class CompleteSpacedReviewResponse(BaseModel):
    success: bool = True
    review_id: str
    interval_step: int
    next_due_at: str
    streak: int


# ============================================================================
# ERROR NOTEBOOK / MISTAKE CARDS
# ============================================================================

class MistakeCardOut(BaseModel):
    id: str
    subject: Optional[str] = None
    topic: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    error_reason_code: str
    prompt_snapshot: str
    correct_explanation: Optional[str] = None
    times_seen: int
    times_repeated: int
    last_seen_at: str
    next_due_at: Optional[str] = None
    status: str
    created_at: str
    updated_at: str


class MistakeCardListResponse(BaseModel):
    success: bool = True
    cards: List[MistakeCardOut] = Field(default_factory=list)
    total: int = 0


class UpdateMistakeCardRequest(BaseModel):
    status: Optional[str] = Field(default=None, pattern=r"^(active|resolved)$")
    error_reason_code: Optional[str] = Field(default=None, max_length=40)
    correct_explanation: Optional[str] = None
    next_due_at: Optional[str] = None  # ISO datetime


class UpdateMistakeCardResponse(BaseModel):
    success: bool = True
    card: MistakeCardOut


# ============================================================================
# ADAPTIVE PLANNER
# ============================================================================

class PlannerTaskOut(BaseModel):
    id: str
    task_date: str
    task_type: str
    subject: Optional[str] = None
    topic: Optional[str] = None
    recommended_minutes: int
    priority_score: float
    status: str
    completed_at: Optional[str] = None
    created_at: str
    updated_at: str


class GenerateDailyPlanRequest(BaseModel):
    date: Optional[str] = None  # YYYY-MM-DD
    available_minutes: int = Field(..., ge=30, le=960)


class StrategistPlanRequest(BaseModel):
    date: Optional[str] = None  # YYYY-MM-DD


class GenerateDailyPlanResponse(BaseModel):
    success: bool = True
    date: str
    generated_count: int
    available_minutes: int
    planned_minutes: int
    tasks: List[PlannerTaskOut] = Field(default_factory=list)


class PlannerDailyResponse(BaseModel):
    success: bool = True
    date: str
    total: int
    planned_minutes: int
    completed_count: int
    skipped_count: int
    pending_count: int
    day_adherence_percent: float = 0.0
    weekly_adherence_percent: float = 0.0
    tasks: List[PlannerTaskOut] = Field(default_factory=list)


class UpdatePlannerTaskRequest(BaseModel):
    status: str = Field(..., pattern=r"^(pending|completed|skipped)$")


class UpdatePlannerTaskResponse(BaseModel):
    success: bool = True
    task: PlannerTaskOut
    rescheduled_task: Optional[PlannerTaskOut] = None


# ============================================================================
# EXAM STAMINA
# ============================================================================

class StartStaminaSessionRequest(BaseModel):
    mode: str = Field(default="mixed", pattern=r"^(mixed|subject)$")
    subject: Optional[SubjectEnum] = None
    topic: Optional[str] = Field(default=None, max_length=160)
    duration_minutes: int = Field(default=30, ge=10, le=180)
    planned_questions: int = Field(default=30, ge=5, le=300)
    block_count: int = Field(default=3, ge=1, le=6)


class StaminaBlockPlanOut(BaseModel):
    block_no: int
    planned_minutes: int
    planned_questions: int


class StartStaminaSessionResponse(BaseModel):
    success: bool = True
    session_id: str
    mode: str
    subject: Optional[str] = None
    topic: Optional[str] = None
    duration_minutes: int
    planned_questions: int
    started_at: str
    block_plan: List[StaminaBlockPlanOut] = Field(default_factory=list)


class FinishStaminaBlockResultIn(BaseModel):
    block_no: int = Field(..., ge=1, le=12)
    attempted_questions: int = Field(..., ge=0, le=500)
    correct_answers: int = Field(..., ge=0, le=500)
    elapsed_sec: int = Field(..., ge=1, le=7200)
    dominant_error: Optional[str] = Field(default=None, pattern=r"^(formula_error|concept_confusion|misread|time_pressure|other)$")


class FinishStaminaSessionRequest(BaseModel):
    block_results: List[FinishStaminaBlockResultIn] = Field(default_factory=list)
    notes: Optional[str] = Field(default=None, max_length=1200)


class FinishStaminaSessionResponse(BaseModel):
    success: bool = True
    session_id: str
    completed_at: str
    total_questions: int
    correct_answers: int
    score_percent: float
    pacing_qph: float
    fatigue_accuracy_dip: float
    fatigue_detected: bool
    error_clusters: dict = Field(default_factory=dict)
    xp_awarded: int = 0


# ============================================================================
# SYNC JOURNAL
# ============================================================================

class SyncOperationIn(BaseModel):
    operation_type: str = Field(..., pattern=r"^(create|update|delete|event)$")
    entity_type: str = Field(..., min_length=1, max_length=40)
    entity_id: Optional[str] = Field(default=None, max_length=80)
    payload: dict = Field(default_factory=dict)
    idempotency_key: str = Field(..., min_length=1, max_length=160)


class SyncBatchRequest(BaseModel):
    operations: List[SyncOperationIn] = Field(..., min_length=1, max_length=500)


class SyncBatchResultItemOut(BaseModel):
    idempotency_key: str
    status: str
    journal_id: Optional[str] = None
    attempt_count: int = 0
    retryable: bool = False
    message: Optional[str] = None


class SyncBatchResponse(BaseModel):
    success: bool = True
    accepted_count: int = 0
    duplicate_count: int = 0
    failed_count: int = 0
    results: List[SyncBatchResultItemOut] = Field(default_factory=list)


class SyncStatusResponse(BaseModel):
    success: bool = True
    pending_count: int = 0
    synced_count: int = 0
    failed_count: int = 0
    total_count: int = 0
    backlog_count: int = 0
    latest_synced_at: Optional[str] = None
