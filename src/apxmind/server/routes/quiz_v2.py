"""
Quiz V2 Router
===============

DB-persisted quiz lifecycle (blueprint §3.5 + §5.4).

POST   /api/quiz                              — start quiz (generate + persist)
GET    /api/quiz                              — list past quizzes
GET    /api/quiz/{quiz_id}                    — quiz metadata
GET    /api/quiz/{quiz_id}/questions          — all questions (no correct_answer)
POST   /api/quiz/{quiz_id}/answers            — submit answer for one question
PUT    /api/quiz/{quiz_id}/answers/{q_id}     — update answer before finishing
POST   /api/quiz/{quiz_id}/finish             — finish, create summary, award XP
PATCH  /api/quiz/{quiz_id}/abandon            — mark abandoned
GET    /api/quiz/{quiz_id}/results            — full results with answers + score
DELETE /api/quiz/{quiz_id}                    — delete quiz + cascade
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user
from ...api.schemas import (
    FinishQuizResponse,
    QuizListResponse,
    QuizMetaOut,
    QuizQuestionOut,
    QuizResultQuestion,
    QuizResultsResponse,
    QuizSummaryOut,
    StartQuizRequest,
    StartQuizResponse,
    SubmitAnswerOut,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    UpdateAnswerRequest,
)
from ...core.dependencies import get_creative_llm, get_llm, get_vectorstore
from ...db.gamification import append_event, award_xp_for_event
from ...db.models import (
    Quiz,
    QuizAttemptAnswer,
    QuizAttemptSummary,
    QuizQuestion,
    MistakeCard,
    TopicMastery,
    User,
    UserBadge,
    BadgeDefinition,
)
from ...db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

XP_PER_CORRECT = 4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _quiz_to_meta(quiz: Quiz) -> QuizMetaOut:
    return QuizMetaOut(
        id=quiz.id,
        subject=quiz.subject,
        topic=quiz.topic,
        difficulty=quiz.difficulty,
        question_count=quiz.question_count,
        time_limit_sec=quiz.time_limit_sec,
        status=quiz.status,
        started_at=quiz.started_at.isoformat(),
        completed_at=quiz.completed_at.isoformat() if quiz.completed_at else None,
    )


def _question_to_out(q: QuizQuestion) -> QuizQuestionOut:
    return QuizQuestionOut(
        id=q.id,
        question_no=q.question_no,
        question_text=q.question_text,
        options=q.options or [],
        topic=q.topic,
        difficulty=q.difficulty,
    )


def _summary_to_out(s: QuizAttemptSummary) -> QuizSummaryOut:
    return QuizSummaryOut(
        id=s.id,
        quiz_id=s.quiz_id,
        subject=s.subject,
        difficulty=s.difficulty,
        correct_answers=s.correct_answers,
        total_questions=s.total_questions,
        score_percent=float(s.score_percent),
        xp_awarded=s.xp_awarded,
        time_taken_sec=s.time_taken_sec,
        created_at=s.created_at.isoformat(),
    )


async def _get_quiz_or_404(db: AsyncSession, quiz_id: str, user_id: int) -> Quiz:
    result = await db.execute(
        select(Quiz).where(Quiz.id == quiz_id, Quiz.user_id == user_id)
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz


# ---------------------------------------------------------------------------
# Question generation (reuses trainer.py logic)
# ---------------------------------------------------------------------------

def _generate_questions_vectorstore(subject, difficulty, count, topic):
    question_bank = get_vectorstore("question_bank")
    if not question_bank:
        return []
    try:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import PromptTemplate

        llm = get_creative_llm()
        topic_hint = f" on topic: {topic}" if topic else ""
        retriever = question_bank.as_retriever(search_kwargs={"k": count * 2})
        docs = retriever.invoke(f"{subject} {difficulty} NEET questions{topic_hint}")
        context = "\n\n".join(doc.page_content for doc in docs[: count * 2])

        prompt = PromptTemplate.from_template(
            "Based on the following NEET exam content, generate {count} MCQs "
            "for {subject} at {difficulty} difficulty{topic_hint}.\n\n"
            "Context:\n{context}\n\n"
            "Return ONLY a JSON array. Each object must have: "
            "question_text (string), options (array of 4 strings), "
            "correct_answer (one of the options verbatim), explanation (string), topic (string).\n\n"
            "JSON:"
        )
        chain = prompt | llm | StrOutputParser()
        raw = chain.invoke(
            {
                "count": count,
                "subject": subject,
                "difficulty": difficulty,
                "topic_hint": topic_hint,
                "context": context,
            }
        )
        # Strip markdown fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()

        return json.loads(raw)
    except Exception as exc:
        logger.warning(f"Vectorstore quiz generation failed: {exc}")
        return []


_SAMPLE_QUESTIONS = {
    "biology": [
        ("What is the powerhouse of the cell?", ["Nucleus", "Mitochondria", "Ribosome", "Golgi body"], "Mitochondria", "Mitochondria produce ATP via cellular respiration."),
        ("Which organelle performs photosynthesis?", ["Mitochondria", "Chloroplast", "Nucleus", "ER"], "Chloroplast", "Chloroplasts contain chlorophyll and carry out photosynthesis."),
        ("DNA replication occurs in which phase?", ["G1", "S", "G2", "M"], "S", "DNA is synthesised in the S (synthesis) phase of the cell cycle."),
        ("Which vitamin is synthesised by skin in sunlight?", ["Vitamin A", "Vitamin B", "Vitamin C", "Vitamin D"], "Vitamin D", "UVB in sunlight converts 7-dehydrocholesterol to Vitamin D3."),
        ("The largest organ of the human body is?", ["Liver", "Skin", "Brain", "Heart"], "Skin", "The skin accounts for about 15% of body weight."),
    ],
    "chemistry": [
        ("Atomic number of Carbon is?", ["4", "6", "8", "12"], "6", "Carbon has 6 protons in its nucleus."),
        ("Most abundant gas in Earth's atmosphere?", ["Oxygen", "Nitrogen", "CO2", "Argon"], "Nitrogen", "Nitrogen makes up ~78% of the atmosphere."),
        ("pH of pure water at 25°C?", ["6", "7", "8", "14"], "7", "Pure water is neutral with pH 7 at 25°C."),
        ("Element with highest electronegativity?", ["Oxygen", "Chlorine", "Fluorine", "Nitrogen"], "Fluorine", "Fluorine has the highest electronegativity (3.98 on Pauling scale)."),
        ("Avogadro's number is approximately?", ["6.02×10²²", "6.02×10²³", "6.02×10²⁴", "3.14×10²³"], "6.02×10²³", "One mole of any substance contains 6.022×10²³ particles."),
    ],
    "physics": [
        ("SI unit of force?", ["Joule", "Newton", "Watt", "Pascal"], "Newton", "Force = mass × acceleration; 1 N = 1 kg·m/s²."),
        ("Speed of light in vacuum?", ["3×10⁶ m/s", "3×10⁸ m/s", "3×10¹⁰ m/s", "3×10⁴ m/s"], "3×10⁸ m/s", "c ≈ 2.998×10⁸ m/s in vacuum."),
        ("F = ma is Newton's?", ["First law", "Second law", "Third law", "Zeroth law"], "Second law", "Newton's second law: net force = mass × acceleration."),
        ("SI unit of electric current?", ["Volt", "Ohm", "Ampere", "Watt"], "Ampere", "Current is measured in Amperes (Coulombs per second)."),
        ("Acceleration due to gravity (approx.)?", ["8.9 m/s²", "9.8 m/s²", "10.8 m/s²", "11.2 m/s²"], "9.8 m/s²", "g ≈ 9.8 m/s² at Earth's surface."),
    ],
}


def _generate_sample_questions(subject, difficulty, count, topic):
    bank = _SAMPLE_QUESTIONS.get(subject, _SAMPLE_QUESTIONS["biology"])[:count]
    return [
        {
            "question_text": q[0],
            "options": q[1],
            "correct_answer": q[2],
            "explanation": q[3],
            "topic": topic or "",
        }
        for q in bank
    ]


async def _upsert_mistake_card(
    db: AsyncSession,
    user_id: int,
    quiz: Quiz,
    question: QuizQuestion,
):
    """Create or update error notebook card for wrong answers."""
    now = datetime.utcnow()
    card_result = await db.execute(
        select(MistakeCard).where(
            MistakeCard.user_id == user_id,
            MistakeCard.subject == quiz.subject,
            MistakeCard.topic == (question.topic or ""),
            MistakeCard.prompt_snapshot == question.question_text,
            MistakeCard.status == "active",
        )
    )
    card = card_result.scalar_one_or_none()

    if card:
        card.times_seen += 1
        card.times_repeated += 1
        card.last_seen_at = now
        card.next_due_at = now + timedelta(days=1)
        if question.explanation and not card.correct_explanation:
            card.correct_explanation = question.explanation
        card.updated_at = now
        return

    db.add(
        MistakeCard(
            user_id=user_id,
            subject=quiz.subject,
            topic=question.topic or "",
            source_type="quiz",
            source_id=quiz.id,
            error_reason_code="concept_confusion",
            prompt_snapshot=question.question_text,
            correct_explanation=question.explanation,
            times_seen=1,
            times_repeated=0,
            last_seen_at=now,
            next_due_at=now + timedelta(days=1),
            status="active",
        )
    )


async def _upsert_topic_mastery(
    db: AsyncSession,
    user_id: int,
    subject: str,
    topic: str,
    is_correct: bool,
):
    """Update mastery score and confidence from quiz answer quality."""
    topic_key = topic.strip() if topic and topic.strip() else "general"
    observed_score = 92.0 if is_correct else 28.0
    observed_confidence = 72.0 if is_correct else 35.0
    now = datetime.utcnow()

    result = await db.execute(
        select(TopicMastery).where(
            TopicMastery.user_id == user_id,
            TopicMastery.subject == subject,
            TopicMastery.topic == topic_key,
        )
    )
    row = result.scalar_one_or_none()

    if row:
        row.mastery_score = round(float(row.mastery_score) * 0.75 + observed_score * 0.25, 2)
        row.confidence = round(float(row.confidence) * 0.7 + observed_confidence * 0.3, 2)
        row.last_assessed_at = now
        return

    db.add(
        TopicMastery(
            user_id=user_id,
            subject=subject,
            topic=topic_key,
            mastery_score=round(observed_score, 2),
            confidence=round(observed_confidence, 2),
            last_assessed_at=now,
        )
    )


# ---------------------------------------------------------------------------
# POST /api/quiz  — start quiz
# ---------------------------------------------------------------------------

@router.post("", response_model=StartQuizResponse, status_code=status.HTTP_201_CREATED)
async def start_quiz(
    request: StartQuizRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subject = request.subject.value
    difficulty = request.difficulty
    count = request.question_count
    topic = request.topic

    # Generate questions
    raw_qs = _generate_questions_vectorstore(subject, difficulty, count, topic)
    if not raw_qs:
        raw_qs = _generate_sample_questions(subject, difficulty, count, topic)

    raw_qs = raw_qs[:count]

    # Persist quiz record
    quiz = Quiz(
        id=str(uuid.uuid4()),
        user_id=user.id,
        subject=subject,
        topic=topic,
        difficulty=difficulty,
        question_count=len(raw_qs),
        time_limit_sec=request.time_limit_sec,
        status="active",
    )
    db.add(quiz)
    await db.flush()

    # Persist questions
    questions_out = []
    for i, q in enumerate(raw_qs):
        qq = QuizQuestion(
            quiz_id=quiz.id,
            question_no=i + 1,
            question_text=q.get("question_text") or q.get("question", ""),
            options=q.get("options", []),
            correct_answer=q.get("correct_answer", ""),
            explanation=q.get("explanation", ""),
            topic=q.get("topic", topic or ""),
            difficulty=difficulty,
        )
        db.add(qq)
        await db.flush()
        questions_out.append(_question_to_out(qq))

    await db.commit()
    await db.refresh(quiz)

    return StartQuizResponse(quiz=_quiz_to_meta(quiz), questions=questions_out)


# ---------------------------------------------------------------------------
# GET /api/quiz  — list history
# ---------------------------------------------------------------------------

@router.get("", response_model=QuizListResponse)
async def list_quizzes(
    subject: str = Query(default=None),
    quiz_status: str = Query(default=None, alias="status"),
    difficulty: str = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filters = [Quiz.user_id == user.id]
    if subject:
        filters.append(Quiz.subject == subject)
    if quiz_status:
        filters.append(Quiz.status == quiz_status)
    if difficulty:
        filters.append(Quiz.difficulty == difficulty)

    total_result = await db.execute(
        select(func.count()).select_from(Quiz).where(*filters)
    )
    total = int(total_result.scalar_one() or 0)

    stmt = (
        select(Quiz)
        .where(*filters)
        .order_by(Quiz.started_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(stmt)
    quizzes = result.scalars().all()
    return QuizListResponse(quizzes=[_quiz_to_meta(q) for q in quizzes], total=total)


# ---------------------------------------------------------------------------
# GET /api/quiz/{quiz_id}
# ---------------------------------------------------------------------------

@router.get("/{quiz_id}", response_model=QuizMetaOut)
async def get_quiz(
    quiz_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    quiz = await _get_quiz_or_404(db, quiz_id, user.id)
    return _quiz_to_meta(quiz)


# ---------------------------------------------------------------------------
# GET /api/quiz/{quiz_id}/questions
# ---------------------------------------------------------------------------

@router.get("/{quiz_id}/questions", response_model=list[QuizQuestionOut])
async def get_quiz_questions(
    quiz_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_quiz_or_404(db, quiz_id, user.id)
    result = await db.execute(
        select(QuizQuestion)
        .where(QuizQuestion.quiz_id == quiz_id)
        .order_by(QuizQuestion.question_no)
    )
    return [_question_to_out(q) for q in result.scalars().all()]


# ---------------------------------------------------------------------------
# POST /api/quiz/{quiz_id}/answers  — submit answer
# ---------------------------------------------------------------------------

@router.post("/{quiz_id}/answers", response_model=SubmitAnswerResponse)
async def submit_answer(
    quiz_id: str,
    request: SubmitAnswerRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    quiz = await _get_quiz_or_404(db, quiz_id, user.id)
    if quiz.status != "active":
        raise HTTPException(status_code=400, detail="Quiz is not active")

    # Fetch question
    q_result = await db.execute(
        select(QuizQuestion).where(
            QuizQuestion.id == request.question_id,
            QuizQuestion.quiz_id == quiz_id,
        )
    )
    question = q_result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found in this quiz")

    is_correct = request.user_answer.strip().lower() == question.correct_answer.strip().lower()
    score = XP_PER_CORRECT if is_correct else 0

    # Upsert answer (replace if answer already exists)
    existing = await db.execute(
        select(QuizAttemptAnswer).where(
            QuizAttemptAnswer.quiz_id == quiz_id,
            QuizAttemptAnswer.question_id == request.question_id,
        )
    )
    ans = existing.scalar_one_or_none()
    if ans:
        ans.user_answer = request.user_answer
        ans.is_correct = is_correct
        ans.score_awarded = score
    else:
        ans = QuizAttemptAnswer(
            quiz_id=quiz_id,
            question_id=request.question_id,
            user_answer=request.user_answer,
            is_correct=is_correct,
            score_awarded=score,
        )
        db.add(ans)

    if not is_correct:
        await _upsert_mistake_card(db, user.id, quiz, question)

    await _upsert_topic_mastery(
        db,
        user_id=user.id,
        subject=quiz.subject,
        topic=question.topic or quiz.topic or "general",
        is_correct=is_correct,
    )

    # Append event
    await append_event(
        db,
        user_id=user.id,
        event_type="quiz_answer_submitted",
        subject=quiz.subject,
        entity_type="quiz",
        entity_id=quiz_id,
        payload={
            "question_id": request.question_id,
            "is_correct": is_correct,
            "confidence_level": request.confidence_level,
        },
    )

    if request.confidence_level is not None:
        await append_event(
            db,
            user_id=user.id,
            event_type="confidence_recorded",
            subject=quiz.subject,
            entity_type="quiz_question",
            entity_id=str(request.question_id),
            event_value=float(request.confidence_level),
            payload={
                "quiz_id": quiz_id,
                "question_id": request.question_id,
                "confidence_level": request.confidence_level,
                "is_correct": is_correct,
            },
        )

    await db.commit()

    # Generate explanation via LLM (best-effort)
    explanation = question.explanation or ""
    if not explanation:
        try:
            from langchain_core.output_parsers import StrOutputParser
            from langchain_core.prompts import PromptTemplate

            llm = get_llm()
            prompt = PromptTemplate.from_template(
                "Briefly explain (2-3 sentences) why '{answer}' is the correct answer "
                "to this NEET question: {question}"
            )
            explanation = (prompt | llm | StrOutputParser()).invoke(
                {"answer": question.correct_answer, "question": question.question_text}
            )
        except Exception:
            explanation = ""

    return SubmitAnswerResponse(
        result=SubmitAnswerOut(
            is_correct=is_correct,
            correct_answer=question.correct_answer,
            explanation=explanation,
            score_awarded=score,
        )
    )


# ---------------------------------------------------------------------------
# PUT /api/quiz/{quiz_id}/answers/{question_id}  — update answer
# ---------------------------------------------------------------------------

@router.put("/{quiz_id}/answers/{question_id}", response_model=SubmitAnswerResponse)
async def update_answer(
    quiz_id: str,
    question_id: int,
    request: UpdateAnswerRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    quiz = await _get_quiz_or_404(db, quiz_id, user.id)
    if quiz.status != "active":
        raise HTTPException(status_code=400, detail="Quiz is not active")

    q_result = await db.execute(
        select(QuizQuestion).where(
            QuizQuestion.id == question_id, QuizQuestion.quiz_id == quiz_id
        )
    )
    question = q_result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    ans_result = await db.execute(
        select(QuizAttemptAnswer).where(
            QuizAttemptAnswer.quiz_id == quiz_id,
            QuizAttemptAnswer.question_id == question_id,
        )
    )
    ans = ans_result.scalar_one_or_none()
    if not ans:
        raise HTTPException(status_code=404, detail="No existing answer — use POST to submit first")

    is_correct = request.user_answer.strip().lower() == question.correct_answer.strip().lower()
    ans.user_answer = request.user_answer
    ans.is_correct = is_correct
    ans.score_awarded = XP_PER_CORRECT if is_correct else 0

    if not is_correct:
        await _upsert_mistake_card(db, user.id, quiz, question)

    await _upsert_topic_mastery(
        db,
        user_id=user.id,
        subject=quiz.subject,
        topic=question.topic or quiz.topic or "general",
        is_correct=is_correct,
    )

    if request.confidence_level is not None:
        await append_event(
            db,
            user_id=user.id,
            event_type="confidence_recorded",
            subject=quiz.subject,
            entity_type="quiz_question",
            entity_id=str(question_id),
            event_value=float(request.confidence_level),
            payload={
                "quiz_id": quiz_id,
                "question_id": question_id,
                "confidence_level": request.confidence_level,
                "is_correct": is_correct,
            },
        )

    await db.commit()

    return SubmitAnswerResponse(
        result=SubmitAnswerOut(
            is_correct=is_correct,
            correct_answer=question.correct_answer,
            score_awarded=ans.score_awarded,
        )
    )


# ---------------------------------------------------------------------------
# POST /api/quiz/{quiz_id}/finish  — finish quiz
# ---------------------------------------------------------------------------

@router.post("/{quiz_id}/finish", response_model=FinishQuizResponse)
async def finish_quiz(
    quiz_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    quiz = await _get_quiz_or_404(db, quiz_id, user.id)
    if quiz.status != "active":
        raise HTTPException(status_code=400, detail="Quiz is already finished or abandoned")

    # Check if summary already exists (idempotent finish)
    existing_summary = await db.execute(
        select(QuizAttemptSummary).where(QuizAttemptSummary.quiz_id == quiz_id)
    )
    if existing_summary.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Quiz already finished")

    # Tally answers
    answers_result = await db.execute(
        select(QuizAttemptAnswer).where(QuizAttemptAnswer.quiz_id == quiz_id)
    )
    answers = answers_result.scalars().all()
    correct = sum(1 for a in answers if a.is_correct)
    total = quiz.question_count
    score_pct = round((correct / total * 100) if total > 0 else 0, 2)
    xp = correct * XP_PER_CORRECT

    # Update quiz status
    quiz.status = "completed"
    quiz.completed_at = datetime.utcnow()

    # Create summary
    summary = QuizAttemptSummary(
        quiz_id=quiz_id,
        user_id=user.id,
        subject=quiz.subject,
        difficulty=quiz.difficulty,
        correct_answers=correct,
        total_questions=total,
        score_percent=score_pct,
        xp_awarded=xp,
    )
    db.add(summary)
    await db.flush()

    # Append event + award XP
    await append_event(
        db,
        user_id=user.id,
        event_type="quiz_completed",
        subject=quiz.subject,
        entity_type="quiz",
        entity_id=quiz_id,
        event_value=float(score_pct),
        payload={"correct": correct, "total": total, "xp": xp},
    )
    await award_xp_for_event(
        db,
        user.id,
        "quiz_completed",
        subject=quiz.subject,
        correct_answers=correct,
    )

    # Check score-based badges (e.g. perfect_quiz, physicist)
    await _check_score_badges(db, user.id, quiz.subject, score_pct)

    await db.commit()
    await db.refresh(summary)

    return FinishQuizResponse(summary=_summary_to_out(summary))


async def _check_score_badges(db, user_id, subject, score_pct):
    """Award score-based badges (90%+ subject ace, 100% perfect)."""
    from ...db.models import UserBadge

    badge_ids = []
    if score_pct >= 100:
        badge_ids.append("perfect_quiz")
    if score_pct >= 90:
        badge_ids.append({"physics": "physicist", "chemistry": "chemist", "biology": "biologist"}.get(subject))

    earned_result = await db.execute(
        select(UserBadge.badge_id).where(UserBadge.user_id == user_id)
    )
    earned_ids = {r[0] for r in earned_result.fetchall()}

    for bid in badge_ids:
        if bid and bid not in earned_ids:
            badge_exists = await db.execute(
                select(BadgeDefinition).where(BadgeDefinition.id == bid)
            )
            if badge_exists.scalar_one_or_none():
                db.add(UserBadge(user_id=user_id, badge_id=bid, earned_at=datetime.utcnow()))
    await db.flush()


# ---------------------------------------------------------------------------
# PATCH /api/quiz/{quiz_id}/abandon
# ---------------------------------------------------------------------------

@router.patch("/{quiz_id}/abandon")
async def abandon_quiz(
    quiz_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    quiz = await _get_quiz_or_404(db, quiz_id, user.id)
    if quiz.status != "active":
        raise HTTPException(status_code=400, detail="Quiz is not active")
    quiz.status = "abandoned"
    await db.commit()
    return {"success": True, "quiz_id": quiz_id, "status": "abandoned"}


# ---------------------------------------------------------------------------
# GET /api/quiz/{quiz_id}/results
# ---------------------------------------------------------------------------

@router.get("/{quiz_id}/results", response_model=QuizResultsResponse)
async def get_quiz_results(
    quiz_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    quiz = await _get_quiz_or_404(db, quiz_id, user.id)

    questions_result = await db.execute(
        select(QuizQuestion)
        .where(QuizQuestion.quiz_id == quiz_id)
        .order_by(QuizQuestion.question_no)
    )
    questions = questions_result.scalars().all()

    answers_result = await db.execute(
        select(QuizAttemptAnswer).where(QuizAttemptAnswer.quiz_id == quiz_id)
    )
    ans_map = {a.question_id: a for a in answers_result.scalars().all()}

    result_questions = [
        QuizResultQuestion(
            question_no=q.question_no,
            question_text=q.question_text,
            options=q.options or [],
            correct_answer=q.correct_answer,
            user_answer=ans_map[q.id].user_answer if q.id in ans_map else None,
            is_correct=ans_map[q.id].is_correct if q.id in ans_map else None,
            explanation=q.explanation,
        )
        for q in questions
    ]

    summary_result = await db.execute(
        select(QuizAttemptSummary).where(QuizAttemptSummary.quiz_id == quiz_id)
    )
    summary = summary_result.scalar_one_or_none()

    return QuizResultsResponse(
        quiz=_quiz_to_meta(quiz),
        questions=result_questions,
        summary=_summary_to_out(summary) if summary else None,
    )


# ---------------------------------------------------------------------------
# DELETE /api/quiz/{quiz_id}
# ---------------------------------------------------------------------------

@router.delete("/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quiz(
    quiz_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    quiz = await _get_quiz_or_404(db, quiz_id, user.id)
    await db.delete(quiz)
    await db.commit()
