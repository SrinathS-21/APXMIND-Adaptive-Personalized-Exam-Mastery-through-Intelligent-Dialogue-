"""
Insights Router
================

Topic mastery, exam readiness snapshots, and daily habit signals.

GET /api/insights/mastery              — all topic mastery (filterable by subject)
GET /api/insights/mastery/{subject}    — mastery for a single subject
GET /api/insights/readiness            — exam readiness snapshots (?days=30)
GET /api/insights/habits               — daily habit signals  (?days=7)
"""

import logging
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.middleware.auth import get_current_user
from ...api.schemas import (
    CalibrationInsightsResponse,
    CalibrationTrendPointOut,
    ExamReadinessListResponse,
    ExamReadinessOut,
    HabitSignalOut,
    HabitSignalsResponse,
    TrendPointOut,
    TopicRiskListResponse,
    TopicRiskOut,
    TopicMasteryListResponse,
    TopicMasteryOut,
    WeeklyReportExportOut,
    WeeklyReportResponse,
    WeeklyReportSummaryOut,
)
from ...db.models import (
    ExamReadinessSnapshot,
    HabitSignal,
    LearningEvent,
    MistakeCard,
    QuizAttemptSummary,
    TopicMastery,
    User,
)
from ...db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Topic Mastery
# ---------------------------------------------------------------------------

def _mastery_state_label(score: float) -> str:
    if score < 35:
        return "Not Started"
    if score < 70:
        return "Shaky"
    return "Strong"

def _mastery_to_out(r: TopicMastery) -> TopicMasteryOut:
    mastery_score = float(r.mastery_score)
    return TopicMasteryOut(
        subject=r.subject,
        topic=r.topic,
        mastery_score=mastery_score,
        confidence=float(r.confidence),
        state_label=_mastery_state_label(mastery_score),
        last_assessed_at=r.last_assessed_at.isoformat() if r.last_assessed_at else None,
    )


async def _build_topic_risk_rows(
    db: AsyncSession,
    user_id: int,
    subject: str | None = None,
    limit: int = 10,
) -> list[TopicRiskOut]:
    today = date.today()

    mastery_stmt = select(TopicMastery).where(TopicMastery.user_id == user_id)
    if subject:
        mastery_stmt = mastery_stmt.where(TopicMastery.subject == subject.lower())

    cards_stmt = select(MistakeCard).where(MistakeCard.user_id == user_id)
    if subject:
        cards_stmt = cards_stmt.where(MistakeCard.subject == subject.lower())

    mastery_rows = (await db.execute(mastery_stmt)).scalars().all()
    mistake_cards = (await db.execute(cards_stmt)).scalars().all()

    topic_map: dict[tuple[str, str], dict] = {}

    for row in mastery_rows:
        topic_key = (row.topic or "").strip() or "general"
        key = ((row.subject or "general").lower(), topic_key)
        topic_map[key] = {
            "subject": (row.subject or "general").lower(),
            "topic": topic_key,
            "mastery_score": float(row.mastery_score),
            "confidence": float(row.confidence),
            "last_assessed_at": row.last_assessed_at,
            "repeated_mistakes": 0,
        }

    for card in mistake_cards:
        topic_key = (card.topic or "").strip() or "general"
        key = ((card.subject or "general").lower(), topic_key)
        entry = topic_map.get(key)
        if not entry:
            entry = {
                "subject": (card.subject or "general").lower(),
                "topic": topic_key,
                "mastery_score": 0.0,
                "confidence": 0.0,
                "last_assessed_at": None,
                "repeated_mistakes": 0,
            }
            topic_map[key] = entry
        entry["repeated_mistakes"] += int(card.times_repeated or 0)

    ranked: list[TopicRiskOut] = []
    for value in topic_map.values():
        last_assessed_at = value["last_assessed_at"]
        days_since_last_assessed = (
            max(0, (today - last_assessed_at.date()).days) if last_assessed_at else 30
        )
        mastery_score = float(value["mastery_score"])
        confidence = float(value["confidence"])
        repeated_mistakes = int(value["repeated_mistakes"])

        base_risk = (100.0 - mastery_score) * 0.65
        mistake_risk = min(40.0, repeated_mistakes * 8.0)
        recency_risk = min(30.0, days_since_last_assessed * 1.2)
        confidence_risk = max(0.0, 50.0 - confidence) * 0.2
        risk_score = round(min(100.0, base_risk + mistake_risk + recency_risk + confidence_risk), 2)

        ranked.append(
            TopicRiskOut(
                subject=value["subject"],
                topic=value["topic"],
                mastery_score=mastery_score,
                confidence=confidence,
                state_label=_mastery_state_label(mastery_score),
                repeated_mistakes=repeated_mistakes,
                days_since_last_assessed=days_since_last_assessed,
                risk_score=risk_score,
            )
        )

    ranked.sort(key=lambda item: (item.risk_score, -item.repeated_mistakes), reverse=True)
    return ranked[:limit]


def _trend_points(start_date: date, values_by_date: dict[date, float], days: int) -> list[TrendPointOut]:
    points: list[TrendPointOut] = []
    for idx in range(days):
        point_date = start_date + timedelta(days=idx)
        points.append(
            TrendPointOut(
                date=point_date.isoformat(),
                value=round(float(values_by_date.get(point_date, 0.0)), 2),
            )
        )
    return points


@router.get("/mastery", response_model=TopicMasteryListResponse, summary="All topic mastery")
async def get_topic_mastery(
    subject: str = Query(default=None),
    min_score: float = Query(default=0.0, ge=0.0, le=100.0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return topic mastery scores, sorted highest first."""
    stmt = (
        select(TopicMastery)
        .where(TopicMastery.user_id == user.id)
        .order_by(TopicMastery.mastery_score.desc())
    )
    if subject:
        stmt = stmt.where(TopicMastery.subject == subject.lower())
    if min_score > 0:
        stmt = stmt.where(TopicMastery.mastery_score >= min_score)

    result = await db.execute(stmt)
    rows = result.scalars().all()
    return TopicMasteryListResponse(mastery=[_mastery_to_out(r) for r in rows], total=len(rows))


@router.get("/mastery/{subject}", response_model=TopicMasteryListResponse, summary="Subject topic mastery")
async def get_topic_mastery_by_subject(
    subject: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TopicMastery)
        .where(TopicMastery.user_id == user.id, TopicMastery.subject == subject.lower())
        .order_by(TopicMastery.mastery_score.desc())
    )
    rows = result.scalars().all()
    return TopicMasteryListResponse(mastery=[_mastery_to_out(r) for r in rows], total=len(rows))


@router.get("/risk-topics", response_model=TopicRiskListResponse, summary="Top risk-ranked topics")
async def get_risk_topics(
    subject: str = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sliced = await _build_topic_risk_rows(db=db, user_id=user.id, subject=subject, limit=limit)
    return TopicRiskListResponse(risk_topics=sliced, total=len(sliced))


@router.get("/calibration", response_model=CalibrationInsightsResponse, summary="Confidence calibration insights")
async def get_calibration_insights(
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since_dt = datetime.utcnow() - timedelta(days=days)
    rows = (
        await db.execute(
            select(LearningEvent)
            .where(
                LearningEvent.user_id == user.id,
                LearningEvent.event_type == "confidence_recorded",
                LearningEvent.occurred_at >= since_dt,
            )
            .order_by(LearningEvent.occurred_at.asc())
        )
    ).scalars().all()

    samples: list[tuple[date, float, bool]] = []
    for row in rows:
        payload = row.payload or {}
        confidence_level = payload.get("confidence_level")
        is_correct = payload.get("is_correct")
        if confidence_level is None or is_correct is None:
            continue
        try:
            confidence = float(confidence_level)
        except (TypeError, ValueError):
            continue
        samples.append((row.occurred_at.date(), confidence, bool(is_correct)))

    if not samples:
        return CalibrationInsightsResponse(days=days)

    sample_count = len(samples)
    mean_confidence = sum(item[1] for item in samples) / sample_count
    accuracy_percent = (sum(1 for item in samples if item[2]) / sample_count) * 100
    confidence_percent = (mean_confidence / 5.0) * 100
    confidence_accuracy_gap = confidence_percent - accuracy_percent

    high_conf_samples = [item for item in samples if item[1] >= 4.0]
    high_conf_wrong = sum(1 for item in high_conf_samples if not item[2])
    confident_wrong_rate = (
        (high_conf_wrong / len(high_conf_samples)) * 100 if high_conf_samples else 0.0
    )

    daily: dict[date, list[tuple[float, bool]]] = {}
    for sample_day, confidence, is_correct in samples:
        daily.setdefault(sample_day, []).append((confidence, is_correct))

    trend: list[CalibrationTrendPointOut] = []
    for day_key in sorted(daily.keys()):
        day_values = daily[day_key]
        day_count = len(day_values)
        day_mean_conf = sum(item[0] for item in day_values) / day_count
        day_acc = (sum(1 for item in day_values if item[1]) / day_count) * 100
        day_gap = (day_mean_conf / 5.0) * 100 - day_acc
        trend.append(
            CalibrationTrendPointOut(
                date=day_key.isoformat(),
                mean_confidence=round(day_mean_conf, 2),
                accuracy_percent=round(day_acc, 2),
                confidence_accuracy_gap=round(day_gap, 2),
                sample_count=day_count,
            )
        )

    return CalibrationInsightsResponse(
        days=days,
        sample_count=sample_count,
        mean_confidence=round(mean_confidence, 2),
        accuracy_percent=round(accuracy_percent, 2),
        confidence_accuracy_gap=round(confidence_accuracy_gap, 2),
        confident_wrong_rate=round(confident_wrong_rate, 2),
        trend=trend,
    )


@router.get("/weekly-report", response_model=WeeklyReportResponse, summary="Weekly offline report")
async def get_weekly_report(
    days: int = Query(default=7, ge=3, le=30),
    export_format: str = Query(default="json", pattern=r"^(json|markdown)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    since_dt = datetime.combine(start_date, datetime.min.time())

    event_rows = (
        await db.execute(
            select(LearningEvent).where(
                LearningEvent.user_id == user.id,
                LearningEvent.event_type == "spaced_review_completed",
                LearningEvent.occurred_at >= since_dt,
            )
        )
    ).scalars().all()

    retention_weight_map = {"correct": 1.0, "partial": 0.5, "incorrect": 0.0}
    retention_daily_totals: dict[date, list[float]] = {}
    for row in event_rows:
        event_day = row.occurred_at.date()
        payload = row.payload or {}
        weight = retention_weight_map.get((payload.get("result") or "").lower(), 0.0)
        retention_daily_totals.setdefault(event_day, []).append(weight)

    retention_values: dict[date, float] = {
        day: (sum(vals) / len(vals)) * 100 for day, vals in retention_daily_totals.items() if vals
    }
    retention_score = round((sum(retention_values.values()) / len(retention_values)) if retention_values else 0.0, 2)

    summary_rows = (
        await db.execute(
            select(QuizAttemptSummary).where(
                QuizAttemptSummary.user_id == user.id,
                QuizAttemptSummary.created_at >= since_dt,
            )
        )
    ).scalars().all()

    accuracy_daily_totals: dict[date, list[float]] = {}
    speed_daily_totals: dict[date, list[float]] = {}
    total_correct = 0
    total_questions = 0

    for row in summary_rows:
        report_day = row.created_at.date()
        accuracy_daily_totals.setdefault(report_day, []).append(float(row.score_percent))
        total_correct += int(row.correct_answers)
        total_questions += int(row.total_questions)
        if row.time_taken_sec and row.time_taken_sec > 0 and row.total_questions > 0:
            qph = (float(row.total_questions) * 3600.0) / float(row.time_taken_sec)
            speed_daily_totals.setdefault(report_day, []).append(qph)

    accuracy_values: dict[date, float] = {
        day: (sum(vals) / len(vals)) for day, vals in accuracy_daily_totals.items() if vals
    }
    speed_values: dict[date, float] = {
        day: (sum(vals) / len(vals)) for day, vals in speed_daily_totals.items() if vals
    }

    accuracy_percent = round((total_correct / total_questions) * 100, 2) if total_questions else 0.0
    speed_qph = round((sum(speed_values.values()) / len(speed_values)) if speed_values else 0.0, 2)

    habit_rows = (
        await db.execute(
            select(HabitSignal).where(
                HabitSignal.user_id == user.id,
                HabitSignal.date >= start_date,
            )
        )
    ).scalars().all()
    active_days = sum(1 for row in habit_rows if row.session_count > 0 or row.deep_focus_minutes > 0)
    consistency_score = round((active_days / days) * 100, 2)

    top_risks = await _build_topic_risk_rows(db=db, user_id=user.id, subject=None, limit=10)
    summary = WeeklyReportSummaryOut(
        retention_score=retention_score,
        accuracy_percent=accuracy_percent,
        speed_qph=speed_qph,
        consistency_score=consistency_score,
        active_days=active_days,
        period_days=days,
    )

    retention_trend = _trend_points(start_date=start_date, values_by_date=retention_values, days=days)
    accuracy_trend = _trend_points(start_date=start_date, values_by_date=accuracy_values, days=days)
    speed_trend = _trend_points(start_date=start_date, values_by_date=speed_values, days=days)

    if export_format == "markdown":
        lines = [
            "# APXMIND Weekly Report",
            "",
            f"Period: {start_date.isoformat()} to {end_date.isoformat()}",
            "",
            "## Summary",
            f"- Retention score: {retention_score:.2f}%",
            f"- Accuracy: {accuracy_percent:.2f}%",
            f"- Speed: {speed_qph:.2f} questions/hour",
            f"- Consistency: {consistency_score:.2f}% ({active_days}/{days} active days)",
            "",
            "## Top Risk Topics",
        ]
        if top_risks:
            for idx, item in enumerate(top_risks, start=1):
                lines.append(
                    f"{idx}. {item.subject} - {item.topic} (risk {item.risk_score:.2f}, state {item.state_label})"
                )
        else:
            lines.append("- No risk topics identified for this period.")
        export_payload = WeeklyReportExportOut(format="markdown", content="\n".join(lines))
    else:
        export_payload = WeeklyReportExportOut(
            format="json",
            content=(
                f"{{\"period\":{{\"start\":\"{start_date.isoformat()}\",\"end\":\"{end_date.isoformat()}\"}},"
                f"\"retention_score\":{retention_score},\"accuracy_percent\":{accuracy_percent},"
                f"\"speed_qph\":{speed_qph},\"consistency_score\":{consistency_score}}}"
            ),
        )

    return WeeklyReportResponse(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        summary=summary,
        retention_trend=retention_trend,
        accuracy_trend=accuracy_trend,
        speed_trend=speed_trend,
        risk_topics=top_risks,
        export=export_payload,
    )


# ---------------------------------------------------------------------------
# Exam Readiness
# ---------------------------------------------------------------------------

@router.get("/readiness", response_model=ExamReadinessListResponse, summary="Exam readiness snapshots")
async def get_readiness(
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = date.today() - timedelta(days=days - 1)
    result = await db.execute(
        select(ExamReadinessSnapshot)
        .where(
            ExamReadinessSnapshot.user_id == user.id,
            ExamReadinessSnapshot.snapshot_date >= since,
        )
        .order_by(ExamReadinessSnapshot.snapshot_date.desc())
    )
    rows = result.scalars().all()

    def _row(r: ExamReadinessSnapshot) -> ExamReadinessOut:
        return ExamReadinessOut(
            snapshot_date=r.snapshot_date.isoformat(),
            projected_score=float(r.projected_score) if r.projected_score is not None else None,
            syllabus_coverage_percent=float(r.syllabus_coverage_percent) if r.syllabus_coverage_percent is not None else None,
            accuracy_percent=float(r.accuracy_percent) if r.accuracy_percent is not None else None,
            speed_qph=float(r.speed_qph) if r.speed_qph is not None else None,
            consistency_score=float(r.consistency_score) if r.consistency_score is not None else None,
            risk_band=r.risk_band,
        )

    snapshots = [_row(r) for r in rows]
    return ExamReadinessListResponse(
        latest=snapshots[0] if snapshots else None,
        history=snapshots,
    )


# ---------------------------------------------------------------------------
# Habit Signals
# ---------------------------------------------------------------------------

@router.get("/habits", response_model=HabitSignalsResponse, summary="Daily habit signals")
async def get_habits(
    days: int = Query(default=7, ge=1, le=90),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = date.today() - timedelta(days=days - 1)
    result = await db.execute(
        select(HabitSignal)
        .where(HabitSignal.user_id == user.id, HabitSignal.date >= since)
        .order_by(HabitSignal.date.desc())
    )
    rows = result.scalars().all()
    return HabitSignalsResponse(
        signals=[
            HabitSignalOut(
                date=r.date.isoformat(),
                session_count=r.session_count,
                deep_focus_minutes=r.deep_focus_minutes,
                interruptions_count=r.interruptions_count,
                first_activity_at=r.first_activity_at.isoformat() if r.first_activity_at else None,
                last_activity_at=r.last_activity_at.isoformat() if r.last_activity_at else None,
            )
            for r in rows
        ]
    )
