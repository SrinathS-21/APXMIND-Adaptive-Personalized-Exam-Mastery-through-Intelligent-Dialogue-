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

import asyncio
import json
import logging
import random
import re
import time
import uuid
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
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
from ...core.dependencies import get_creative_llm, get_llm, get_settings, get_vectorstore
from ...core.language import language_name, resolve_request_language
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
QUIZ_GENERATION_TIMEOUT_SEC = 20
QUIZ_EXPLANATION_TIMEOUT_SEC = 10
QUIZ_DYNAMIC_EXAMPLE_TIMEOUT_SEC = 10


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

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_QUESTION_BANK_CHUNKS_FILE = "question_bank_chunks.json"

_SUBJECT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "physics": (
        "physics section",
        "velocity",
        "acceleration",
        "magnetic",
        "electric",
        "newton",
        "wavelength",
        "wave",
        "resistance",
        "current",
        "optics",
    ),
    "chemistry": (
        "chemistry section",
        "molar",
        "electrode",
        "equilibrium",
        "benzene",
        "reaction",
        "organic",
        "enthalpy",
        "thermodynamics",
        "polymer",
        "coordination",
    ),
    "biology": (
        "botany section",
        "zoology section",
        "biology section",
        "cell",
        "photosynthesis",
        "dna",
        "enzyme",
        "plant",
        "animal",
        "ecology",
        "genetics",
    ),
}

_MOJIBAKE_MARKERS = ("Ã", "Â", "â", "ï", "ð", "�")

_TEXT_REPLACEMENTS: dict[str, str] = {
    "â€™": "'",
    "â€˜": "'",
    "â€œ": '"',
    "â€\x9d": '"',
    "â€“": "-",
    "â€”": "-",
    "Â": "",
    "Ã—": "×",
    "Ã·": "÷",
    "Î¼": "µ",
    "Ï€": "π",
    "Î±": "α",
    "Î²": "β",
    "Î³": "γ",
    "Î¸": "θ",
    "Îµ": "ε",
    "ï®": "ν",
    "": "ε",
    "": "ε",
    "∈": "ε",
    "": "µ",
    "": "π",
    "": "θ",
    "": "λ",
    "": "ν",
    "": "Ω",
    "": "×",
    "": "-",
    "": "∝",
    "": "=>",
    "": "->",
    "": "",
    "": "(",
    "": "(",
    "": "(",
    "": ")",
    "": ")",
    "": ")",
    "": "(",
    "": "(",
    "": "(",
    "": ")",
    "": ")",
    "": ")",
    "": "[",
    "": "[",
    "": "[",
    "": "]",
    "": "]",
    "": "]",
    "ˆ": "^",
    "â": "",
    "�": "",
}


def _clean_inline_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _mojibake_score(text: str) -> int:
    if not text:
        return 0
    return sum(text.count(marker) for marker in _MOJIBAKE_MARKERS)


def _decode_latin1_utf8_if_needed(text: str) -> str:
    raw = str(text or "")
    if not raw:
        return ""

    try:
        repaired = raw.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
    except Exception:
        return raw

    # Keep the candidate only when it materially reduces encoding artifacts.
    if not repaired or len(repaired) < max(3, int(len(raw) * 0.7)):
        return raw
    if _mojibake_score(repaired) + 1 < _mojibake_score(raw):
        return repaired
    return raw


def _sanitize_text(text: str) -> str:
    cleaned = _decode_latin1_utf8_if_needed(_clean_inline_text(text))
    for bad, good in _TEXT_REPLACEMENTS.items():
        cleaned = cleaned.replace(bad, good)

    # Remove any remaining private-use glyphs that come from PDF symbol fonts.
    cleaned = re.sub(r"[\uE000-\uF8FF]", " ", cleaned)
    cleaned = re.sub(r"(ε|∈)\s*0", "ε0", cleaned)

    # Normalize OCR fraction artifacts such as "th 1 16 () () ()" -> "1/16th".
    cleaned = re.sub(
        r"\bth\s+(\d+)\s+(\d+)(?:\s*\(\s*\)\s*){0,6}",
        lambda match: f"{match.group(1)}/{match.group(2)}th",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(
        r"\b(\d+)\s+(\d+)(?:\s*\(\s*\)\s*){3,}",
        lambda match: f"{match.group(1)}/{match.group(2)}",
        cleaned,
    )
    cleaned = re.sub(r"(\d+/\d+th)([A-Za-z])", r"\1 \2", cleaned)
    cleaned = re.sub(r"(?:\(\s*\)\s*){2,}", " ", cleaned)

    cleaned = re.sub(r"(?<=\s)â(?=\s|$)", "-", cleaned)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"\(\s+", "(", cleaned)
    cleaned = re.sub(r"\s+\)", ")", cleaned)
    return _clean_inline_text(cleaned)


def _looks_scrambled_formula_text(text: str) -> bool:
    cleaned = _clean_inline_text(text)
    if not cleaned:
        return False

    tokens = cleaned.split()
    if len(tokens) < 4:
        return False

    # If operators are present, the expression is usually still interpretable.
    if any(op in cleaned for op in ("/", "^", "=", "×", "÷", "+", "-", "(", ")", "[", "]", "{", "}", ":", "·")):
        return False

    if any(len(token) >= 4 and token.isalpha() for token in tokens):
        return False

    short_token_count = sum(
        1
        for token in tokens
        if len(token) <= 2
        or bool(re.fullmatch(r"\d{1,4}", token))
        or bool(re.fullmatch(r"[A-Za-z]{1,2}\d*", token))
    )
    alpha_like_count = sum(1 for token in tokens if re.search(r"[A-Za-zεµπθλνΩαβγ]", token))
    digit_like_count = sum(1 for token in tokens if re.search(r"\d", token))

    if len(tokens) == 0:
        return False

    return (
        short_token_count / len(tokens) >= 0.85
        and alpha_like_count >= 2
        and digit_like_count >= 1
    )


def _has_example_block(text: str) -> bool:
    return bool(re.search(r"\bexample\s*:", str(text or ""), flags=re.I))


def _sanitize_multiline_text(text: str) -> str:
    raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = raw.split("\n")
    cleaned_lines = []
    for line in lines:
        cleaned = _sanitize_text(line)
        if cleaned:
            cleaned_lines.append(cleaned)
    return "\n".join(cleaned_lines)


def _with_example_block(text: str) -> str:
    explanation = _sanitize_multiline_text(text)
    if _has_example_block(explanation):
        return explanation
    return (
        f"{explanation}\n\n"
        "Example: Solve a similar NEET-style variant by changing one value and applying the same concept step-by-step."
    )


_GENERIC_EXPLANATION_MARKERS: tuple[str, ...] = (
    "aligns with the governing neet concept",
    "other options violate a key condition",
    "survives elimination against distractors",
    "apply the governing formula or condition in the stem",
)

_LOW_SIGNAL_REASON_MARKERS: tuple[str, ...] = (
    "follows concept",
    "correct option follows",
    "apply formula",
    "by concept",
)

_GENERIC_EXAMPLE_MARKERS: tuple[str, ...] = (
    "similar neet-style variant",
    "replace one given value",
    "apply the same concept step-by-step",
)


def _looks_generic_explanation(text: str) -> bool:
    explanation = _sanitize_text(text).lower()
    if not explanation:
        return True
    return any(marker in explanation for marker in _GENERIC_EXPLANATION_MARKERS)


def _looks_low_signal_reason(text: str) -> bool:
    reason = _sanitize_text(text).lower()
    if not reason:
        return True
    if len(reason.split()) < 8:
        return True
    return any(marker in reason for marker in _LOW_SIGNAL_REASON_MARKERS)


def _looks_generic_example(text: str) -> bool:
    example = _sanitize_text(text).lower()
    if not example:
        return True
    return any(marker in example for marker in _GENERIC_EXAMPLE_MARKERS)


def _stem_snippet(question_text: str, max_chars: int = 140) -> str:
    cleaned = _sanitize_text(question_text)
    if not cleaned:
        return "the given conditions"
    snippet = re.split(r"[.?!]", cleaned, maxsplit=1)[0].strip() or cleaned
    if len(snippet) > max_chars:
        snippet = snippet[:max_chars].rstrip() + "..."
    return snippet


def _question_style(question_text: str) -> str:
    lowered = _sanitize_text(question_text).lower()
    if not lowered:
        return "general"

    if (
        "match column" in lowered
        or "match list" in lowered
        or "column-i" in lowered
        or "column-ii" in lowered
    ):
        return "match"

    if (
        ("assertion" in lowered and "reason" in lowered)
        or ("statement i" in lowered and "statement ii" in lowered)
    ):
        return "assertion_reason"

    if re.search(r"\d", lowered) and any(token in lowered for token in ("=", "sin", "cos", "log", "calculate", "find", "ratio")):
        return "numerical"

    return "conceptual"


def _extract_key_terms(question_text: str, max_terms: int = 3) -> list[str]:
    lowered = _sanitize_text(question_text).lower()
    if not lowered:
        return []

    stop_words = {
        "the", "and", "for", "with", "from", "that", "this", "which", "what", "when", "where",
        "into", "between", "during", "given", "below", "choose", "correct", "answer", "option",
        "options", "column", "statement", "question", "following", "value", "values", "match",
        "column-i", "column-ii", "column-i.", "column-ii.",
    }

    picked: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"[a-z][a-z0-9\-]{2,}", lowered):
        if token in stop_words:
            continue
        if token.isdigit():
            continue
        if token in seen:
            continue
        seen.add(token)
        picked.append(token)
        if len(picked) >= max_terms:
            break
    return picked


def _contains_keyword(text: str, keyword: str) -> bool:
    if not text or not keyword:
        return False
    pattern = r"\\b" + re.escape(keyword).replace(r"\\ ", r"\\s+") + r"\\b"
    return bool(re.search(pattern, text))


def _concept_hint_from_question(question_text: str) -> str:
    lowered = _sanitize_text(question_text).lower()
    if not lowered:
        return "the governing formula or condition in the stem"

    style = _question_style(question_text)
    if style == "match":
        return "pair each item using known concept links and validate all pairs against one option tuple"
    if style == "assertion_reason":
        return "independent truth-check of each statement, then the explanation relationship"

    hint_map: tuple[tuple[tuple[str, ...], str], ...] = (
        (("half-life", "radioactive", "decay"), "the decay relation A = A0 * (1/2)^n"),
        (("capacitor", "electrostatic energy", "electric field"), "capacitor energy and field-capacitance relations"),
        (("lcr", "resonance", "inductance", "reactance"), "LCR resonance relations (X_L = X_C, omega_0 = 1/sqrt(LC))"),
        (("current", "resistance", "voltage", "ohm"), "Ohm's law and equivalent resistance rules"),
        (("projectile", "maximum height", "time of flight"), "standard projectile-motion equations"),
        (("satellite", "gravitational", "orbit"), "orbital and gravitational relations"),
        (("mole", "equilibrium", "ph", "concentration"), "mole-balance and equilibrium relations"),
        (("nitrococcus", "nitrobacter", "rhizobium", "denitrification", "nitrite", "nitrate"), "nitrogen-cycle conversions and associated microbes"),
        (("homologous", "prophase i", "meiosis", "mitosis"), "key phase events in meiosis versus mitosis"),
        (("plasticity", "heterophylly", "buttercup", "maize"), "plant plasticity and heterophylly distinctions"),
        (("electrostatic precipitator", "thermal power plant", "pollutant"), "electrostatic precipitation and particulate removal"),
    )
    for keywords, hint in hint_map:
        if any(_contains_keyword(lowered, keyword) for keyword in keywords):
            return hint

    key_terms = _extract_key_terms(question_text)
    if key_terms:
        return f"the core condition around {', '.join(key_terms)}"
    return "the governing condition in the stem"


def _example_hint_from_question(
    question_text: str,
    correct_answer: str,
    *,
    user_answer: str = "",
    is_correct: bool | None = None,
) -> str:
    cleaned = _sanitize_text(question_text)
    lowered = cleaned.lower()
    style = _question_style(question_text)

    if style == "match":
        sanitized_answer = _sanitize_text(correct_answer)
        return (
            "Build the map in two passes: first lock two sure pairs, then eliminate tuples that violate those pairs. "
            f"Finally verify every remaining pair against the stem; this gives '{sanitized_answer or 'the correct tuple'}'."
        )

    if style == "assertion_reason":
        return (
            "Check Statement I and Statement II separately as true/false, then test whether Statement II explains Statement I. "
            "Pick the option that matches this (truth, explanation) combination."
        )

    if "capacitor" in lowered and ("sin" in lowered or "cos" in lowered or "displacement current" in lowered):
        return (
            "If V(t) = 20 sin(5t) and capacitance C = 2 F, then dV/dt = 100 cos(5t), so "
            "Id = C dV/dt = 200 cos(5t). Use the same derivative step here."
        )

    if any(_contains_keyword(lowered, token) for token in ("half-life", "radioactive", "decay")):
        return (
            "If half-life is 10 min, then after 30 min (three half-lives), activity becomes "
            "A0*(1/2)^3 = A0/8."
        )

    if any(_contains_keyword(lowered, token) for token in ("homologous", "prophase i", "meiosis")):
        return (
            "If asked where synapsis occurs, choose prophase I (meiosis). In mitosis, homologous chromosomes do not pair."
        )

    if any(_contains_keyword(lowered, token) for token in ("plasticity", "heterophylly", "buttercup", "maize")):
        return (
            "If a variant asks for heterophylly, choose the plant showing different leaf forms under different stages/conditions, "
            "and reject grasses that do not show that change."
        )

    number_hits = [
        value
        for value in re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?(?![A-Za-z])", cleaned)
        if value not in {"0", "1"}
    ]
    if number_hits:
        return (
            "Keep the same method, replace one given value "
            f"(for instance {number_hits[0]}) with a nearby value, recompute, and choose the matching option."
        )

    sanitized_answer = _sanitize_text(correct_answer)
    sanitized_user = _sanitize_text(user_answer)
    if is_correct is False and sanitized_user and sanitized_answer:
        return (
            f"Compare '{sanitized_user}' and '{sanitized_answer}' against the stem condition. "
            f"Only '{sanitized_answer}' satisfies all constraints in the question."
        )
    if sanitized_answer:
        return (
            f"Re-check the defining condition in the stem and eliminate options that violate it; "
            f"the surviving option is '{sanitized_answer}'."
        )

    key_terms = _extract_key_terms(question_text)
    if key_terms:
        return (
            f"Use the key terms ({', '.join(key_terms)}) to eliminate mismatching options, then keep the option consistent with all terms."
        )

    return "Identify the key condition in the stem, eliminate conflicting options, and keep the option that fully matches the condition."


def _split_reason_and_example(text: str) -> tuple[str, str]:
    cleaned = _sanitize_multiline_text(text)
    if not cleaned:
        return "", ""

    match = re.search(r"\bexample\s*:\s*", cleaned, flags=re.I)
    if match:
        reason_part = cleaned[:match.start()].strip()
        example_part = cleaned[match.end():].strip()
    else:
        reason_part = cleaned.strip()
        example_part = ""

    reason_part = re.sub(r"^\s*reason\s*:\s*", "", reason_part, flags=re.I)
    return reason_part, example_part


def _compose_explanation(reason: str, example: str) -> str:
    reason_clean = re.sub(r"^\s*reason\s*:\s*", "", _sanitize_text(reason), flags=re.I)
    example_clean = re.sub(r"^\s*example\s*:\s*", "", _sanitize_text(example), flags=re.I)
    return f"Reason:\n{reason_clean}\n\nExample:\n{example_clean}"


def _is_dynamic_example_usable(text: str) -> bool:
    cleaned = _sanitize_text(text)
    if not cleaned:
        return False
    if len(cleaned.split()) < 10:
        return False
    if _looks_generic_example(cleaned):
        return False
    banned_fragments = (
        "apply the same concept",
        "similar variant",
        "replace one given value",
    )
    return not any(fragment in cleaned.lower() for fragment in banned_fragments)


def _normalize_explanation_layout(
    text: str,
    *,
    question_text: str,
    correct_answer: str,
    user_answer: str,
    is_correct: bool | None,
    force_example: bool,
) -> str:
    reason_part, example_part = _split_reason_and_example(text)

    if not reason_part or _looks_generic_explanation(reason_part) or _looks_low_signal_reason(reason_part):
        base = _fallback_explanation(
            correct_answer,
            question_text=question_text,
            user_answer=user_answer,
            is_correct=is_correct,
        )
        reason_part, example_part = _split_reason_and_example(base)
    else:
        chosen = _sanitize_text(user_answer)
        correct = _sanitize_text(correct_answer)
        if is_correct is False and chosen and correct:
            prefix = f"You selected '{chosen}', but the correct answer is '{correct}'. "
            if chosen.lower() not in reason_part.lower() or correct.lower() not in reason_part.lower():
                reason_part = prefix + reason_part
        elif is_correct is True and correct:
            selected = chosen or correct
            if "your answer" not in reason_part.lower() and selected.lower() not in reason_part.lower():
                reason_part = f"Your answer '{selected}' is correct. {reason_part}"

    if force_example or not example_part or _looks_generic_example(example_part):
        example_part = _example_hint_from_question(
            question_text,
            correct_answer,
            user_answer=user_answer,
            is_correct=is_correct,
        )

    return _compose_explanation(reason_part, example_part)


def _is_explanation_usable(text: str) -> bool:
    explanation = _sanitize_text(text)
    if not explanation or len(explanation.split()) < 5:
        return False
    if _looks_generic_explanation(explanation):
        return False
    if _mojibake_score(explanation) >= 5:
        return False
    alnum_ratio = sum(ch.isalnum() for ch in explanation) / max(1, len(explanation))
    return alnum_ratio >= 0.22


def _fallback_explanation(
    correct_answer: str,
    *,
    question_text: str = "",
    user_answer: str = "",
    is_correct: bool | None = None,
) -> str:
    correct = _sanitize_text(correct_answer)
    chosen = _sanitize_text(user_answer)
    stem = _stem_snippet(question_text)
    concept_hint = _concept_hint_from_question(question_text)
    style = _question_style(question_text)
    if style == "assertion_reason":
        key_terms_text = "the truth status of Statement I and Statement II"
    elif style == "match":
        key_terms_text = "the pair-mapping constraints across both columns"
    else:
        key_terms = _extract_key_terms(question_text)
        key_terms_text = ", ".join(key_terms) if key_terms else "the stem conditions"

    if is_correct is None:
        reason = (
            f"Reason: In this question on {stem}, focus on {key_terms_text}. "
            f"Using {concept_hint}, the valid result is '{correct or 'the correct option'}'."
        )
    elif is_correct:
        selected = chosen or correct
        reason = (
            f"Reason: Your answer '{selected}' is correct because it satisfies {key_terms_text}. "
            f"This matches {concept_hint}."
        )
    else:
        chosen_segment = f" You selected '{chosen}'," if chosen else ""
        reason = (
            f"Reason:{chosen_segment} but the key condition is {key_terms_text}. "
            f"Using {concept_hint}, the correct option is '{correct or 'the correct option'}', "
            "while your choice does not satisfy all required conditions."
        )

    example = _example_hint_from_question(
        question_text,
        correct,
        user_answer=chosen,
        is_correct=is_correct,
    )
    return _compose_explanation(reason, example)


def _sanitize_explanation(
    text: str,
    *,
    correct_answer: str = "",
    force_example: bool = False,
    allow_fallback: bool = True,
    question_text: str = "",
    user_answer: str = "",
    is_correct: bool | None = None,
) -> str:
    explanation = _sanitize_multiline_text(text).lstrip(")] -: ")
    if explanation.lower().startswith("sol."):
        explanation = _sanitize_multiline_text(explanation[4:])

    if not _is_explanation_usable(explanation):
        explanation = (
            _fallback_explanation(
                correct_answer,
                question_text=question_text,
                user_answer=user_answer,
                is_correct=is_correct,
            )
            if allow_fallback
            else explanation
        )
    return _normalize_explanation_layout(
        explanation,
        question_text=question_text,
        correct_answer=correct_answer,
        user_answer=user_answer,
        is_correct=is_correct,
        force_example=force_example,
    )


def _infer_subject_from_text(text: str) -> str | None:
    lowered = _sanitize_text(text).lower()
    if not lowered:
        return None

    scores: dict[str, int] = {}
    for subject, terms in _SUBJECT_KEYWORDS.items():
        scores[subject] = sum(1 for term in terms if term in lowered)

    best_subject = max(scores, key=scores.get)
    return best_subject if scores[best_subject] > 0 else None


def _infer_subject_from_question_number(question_no: int | None) -> str | None:
    if not isinstance(question_no, int) or question_no <= 0:
        return None
    # Most NEET papers are organized as Physics -> Chemistry -> Biology.
    if question_no <= 50:
        return "physics"
    if question_no <= 100:
        return "chemistry"
    if question_no <= 220:
        return "biology"
    return None


def _estimate_difficulty(question_text: str, explanation: str) -> str:
    text = f"{_sanitize_text(question_text)} {_sanitize_text(explanation)}".lower()
    numeric_tokens = len(re.findall(r"\d+(?:\.\d+)?", text))
    word_count = len(text.split())

    hard_markers = (
        "assertion",
        "reason",
        "match list",
        "calculate",
        "evaluate",
        "derive",
        "numerical",
        "equilibrium constant",
        "electrode potential",
    )
    easy_markers = (
        "identify",
        "which of the following",
        "not correct",
        "incorrect statement",
    )

    if any(marker in text for marker in hard_markers) or numeric_tokens >= 8 or word_count >= 120:
        return "hard"
    if numeric_tokens <= 2 and word_count <= 45 and any(marker in text for marker in easy_markers):
        return "easy"
    return "medium"


def _difficulty_score(question_text: str, explanation: str) -> int:
    text = f"{_sanitize_text(question_text)} {_sanitize_text(explanation)}".lower()
    numeric_tokens = len(re.findall(r"\d+(?:\.\d+)?", text))
    word_count = len(text.split())

    score = word_count + numeric_tokens * 6
    if any(marker in text for marker in ("assertion", "reason", "calculate", "derive", "numerical")):
        score += 18
    if any(marker in text for marker in ("identify", "which of the following", "incorrect statement")):
        score -= 8
    return max(0, score)


def _rebalance_difficulty_labels(rows: list[dict]) -> list[dict]:
    by_subject: dict[str, list[dict]] = {"physics": [], "chemistry": [], "biology": []}
    for row in rows:
        subject = row.get("subject")
        if subject in by_subject:
            by_subject[subject].append(row)

    for subject_rows in by_subject.values():
        if len(subject_rows) < 10:
            continue

        scores = sorted(int(item.get("difficulty_score", 0)) for item in subject_rows)
        easy_idx = int((len(scores) - 1) * 0.3)
        hard_idx = int((len(scores) - 1) * 0.7)
        easy_cutoff = scores[easy_idx]
        hard_cutoff = scores[hard_idx]

        for item in subject_rows:
            score = int(item.get("difficulty_score", 0))
            if score <= easy_cutoff:
                item["difficulty"] = "easy"
            elif score >= hard_cutoff:
                item["difficulty"] = "hard"
            else:
                item["difficulty"] = "medium"

    return rows


def _extract_question_blocks(raw_text: str) -> list[str]:
    text = _sanitize_text(raw_text)
    if not text:
        return []

    matches = list(re.finditer(r"\b(\d{1,3})\.\s", text))
    blocks: list[str] = []

    for index, match in enumerate(matches):
        try:
            qno = int(match.group(1))
        except Exception:
            continue
        if qno <= 0 or qno > 220:
            continue

        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = _clean_inline_text(text[start:end])
        if len(block.split()) >= 18:
            blocks.append(block)

    return blocks


_VISUAL_CONTEXT_PATTERNS: tuple[str, ...] = (
    "following circuit",
    "circuit shown",
    "shown in the circuit",
    "following figure",
    "figure shown",
    "as shown in figure",
    "from the figure",
    "following graph",
    "graph shown",
    "shown in the graph",
    "table given below",
    "following table",
    "ray diagram",
)


def _requires_visual_context(question_text: str) -> bool:
    lowered = _sanitize_text(question_text).lower()
    if not lowered:
        return False

    if any(pattern in lowered for pattern in _VISUAL_CONTEXT_PATTERNS):
        return True

    # Generic references that usually point to missing visual assets in PDF extraction.
    generic_hits = (
        "diagram" in lowered,
        "figure" in lowered,
        "graph" in lowered,
        "depicted" in lowered,
        "as shown below" in lowered,
    )
    return sum(1 for hit in generic_hits if hit) >= 2


def _parse_block_to_mcq(block: str, source: str, paper_number: int | None) -> dict | None:
    qno_match = re.match(r"\s*(\d{1,3})\.", block)
    question_no = int(qno_match.group(1)) if qno_match else None

    option_matches = list(re.finditer(r"\((1|2|3|4)\)\s*", block))
    if not option_matches:
        return None

    first_idx: dict[int, re.Match] = {}
    for match in option_matches:
        value = int(match.group(1))
        if value not in first_idx:
            first_idx[value] = match
        if len(first_idx) == 4:
            break

    if not all(idx in first_idx for idx in (1, 2, 3, 4)):
        return None

    m1, m2, m3, m4 = first_idx[1], first_idx[2], first_idx[3], first_idx[4]
    if not (m1.start() < m2.start() < m3.start() < m4.start()):
        return None

    answer_match = re.search(r"Answer\s*\((\d)", block)
    option_four_end = answer_match.start() if answer_match and answer_match.start() > m4.end() else len(block)

    question_text = _sanitize_text(block[:m1.start()])
    question_text = re.sub(r"^\d{1,3}\.\s*", "", question_text).strip()
    if len(question_text.split()) < 6:
        return None
    if _looks_scrambled_formula_text(question_text):
        return None
    if _requires_visual_context(question_text):
        return None

    options = [
        _sanitize_text(block[m1.end():m2.start()]),
        _sanitize_text(block[m2.end():m3.start()]),
        _sanitize_text(block[m3.end():m4.start()]),
        _sanitize_text(block[m4.end():option_four_end]),
    ]
    if any(len(option) < 2 for option in options):
        return None
    if any(_looks_scrambled_formula_text(option) for option in options):
        return None

    correct_answer = ""
    if answer_match:
        try:
            ans_idx = int(answer_match.group(1)) - 1
            if 0 <= ans_idx < 4:
                correct_answer = options[ans_idx]
        except Exception:
            correct_answer = ""
    if not correct_answer:
        return None

    explanation = ""
    if answer_match:
        tail = block[answer_match.end():]
        sol_match = re.search(r"Sol\.\s*(.*)", tail, flags=re.S)
        explanation = _sanitize_explanation(
            sol_match.group(1) if sol_match else tail,
            correct_answer=correct_answer,
            question_text=question_text,
        )
    if not explanation:
        explanation = _fallback_explanation(
            correct_answer,
            question_text=question_text,
            is_correct=None,
        )

    subject = _infer_subject_from_question_number(question_no) or _infer_subject_from_text(block)
    if not subject:
        return None

    difficulty = _estimate_difficulty(question_text, explanation)
    difficulty_score = _difficulty_score(question_text, explanation)
    return {
        "question_text": question_text,
        "options": options,
        "correct_answer": correct_answer,
        "explanation": explanation,
        "topic": f"NEET Paper {paper_number}" if paper_number else "NEET Previous Year",
        "subject": subject,
        "difficulty": difficulty,
        "difficulty_score": difficulty_score,
        "question_no": question_no,
        "source": source,
    }


@lru_cache(maxsize=1)
def _load_question_bank_mcqs() -> list[dict]:
    settings = get_settings()
    candidates = [
        Path(settings.chroma_persist_dir) / _QUESTION_BANK_CHUNKS_FILE,
        _PROJECT_ROOT / "data" / "vectorstore" / _QUESTION_BANK_CHUNKS_FILE,
    ]

    chunk_file = next((path for path in candidates if path.exists()), None)
    if not chunk_file:
        logger.warning("Question bank chunk file not found in configured vectorstore paths")
        return []

    try:
        raw = json.loads(chunk_file.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning(f"Failed to read question bank chunks from {chunk_file}: {exc}")
        return []

    chunks = raw.get("chunks") if isinstance(raw, dict) else None
    if not isinstance(chunks, list):
        return []

    parsed: list[dict] = []
    seen: set[str] = set()

    for row in chunks:
        if not isinstance(row, dict):
            continue
        content = _sanitize_text(str(row.get("content") or ""))
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        source = str(metadata.get("source") or "question_bank")
        paper_number_raw = metadata.get("paper_number")
        paper_number = int(paper_number_raw) if isinstance(paper_number_raw, int) else None

        for block in _extract_question_blocks(content):
            mcq = _parse_block_to_mcq(block, source=source, paper_number=paper_number)
            if not mcq:
                continue
            q_key = _sanitize_text(mcq["question_text"]).lower()
            if q_key in seen:
                continue
            seen.add(q_key)
            parsed.append(mcq)

            parsed = _rebalance_difficulty_labels(parsed)

    logger.info(f"Parsed {len(parsed)} NEET MCQs from {chunk_file}")
    return parsed


def _sample_neet_bank_questions(subject: str, difficulty: str, count: int, topic: str | None) -> list[dict]:
    bank = _load_question_bank_mcqs()
    if not bank or count <= 0:
        return []

    subject_pool = [item for item in bank if item.get("subject") == subject]
    if not subject_pool:
        return []

    pool = subject_pool
    if topic:
        topic_lower = topic.strip().lower()
        topic_matched = [
            item for item in subject_pool
            if topic_lower in f"{item.get('topic', '')} {item.get('question_text', '')}".lower()
        ]
        if topic_matched:
            pool = topic_matched

    requested = difficulty.strip().lower()
    if requested == "mixed":
        random.shuffle(pool)
        selected = pool[:count]
    else:
        priority_map = {
            "easy": ["easy", "medium", "hard"],
            "medium": ["medium", "hard", "easy"],
            "hard": ["hard", "medium", "easy"],
        }
        selected = []
        used_ids: set[str] = set()
        for band in priority_map.get(requested, ["medium", "hard", "easy"]):
            subset = [item for item in pool if item.get("difficulty") == band]
            random.shuffle(subset)
            for item in subset:
                qid = _sanitize_text(item.get("question_text", "")).lower()
                if qid in used_ids:
                    continue
                used_ids.add(qid)
                selected.append(item)
                if len(selected) >= count:
                    break
            if len(selected) >= count:
                break

    normalized: list[dict] = []
    for item in selected:
        question_text = _sanitize_text(item.get("question_text", ""))
        options = [_sanitize_text(option) for option in list(item.get("options") or [])[:4]]
        correct_answer = _sanitize_text(item.get("correct_answer", ""))
        if re.fullmatch(r"[1-4]", correct_answer) and 0 < int(correct_answer) <= len(options):
            correct_answer = options[int(correct_answer) - 1]
        if correct_answer not in options and options:
            keyed = {_sanitize_text(option).lower(): option for option in options}
            correct_answer = keyed.get(_sanitize_text(correct_answer).lower(), options[0])

        explanation = _sanitize_explanation(
            item.get("explanation", ""),
            correct_answer=correct_answer,
            force_example=True,
            question_text=question_text,
        )

        normalized.append(
            {
                "question_text": question_text,
                "options": options,
                "correct_answer": correct_answer,
                "explanation": explanation,
                "topic": _sanitize_text(topic or item.get("topic") or "NEET Previous Year"),
            }
        )

    return normalized


def _coerce_generated_questions(raw_items: object, subject: str, difficulty: str, topic: str | None) -> list[dict]:
    if not isinstance(raw_items, list):
        return []

    normalized: list[dict] = []
    for row in raw_items:
        if not isinstance(row, dict):
            continue

        question_text = _sanitize_text(row.get("question_text") or row.get("question") or "")
        options = row.get("options") if isinstance(row.get("options"), list) else []
        options = [_sanitize_text(option) for option in options if _sanitize_text(option)]
        if len(question_text.split()) < 6 or len(options) < 4:
            continue

        options = options[:4]
        correct = _sanitize_text(row.get("correct_answer") or "")
        if re.fullmatch(r"[1-4]", correct):
            correct = options[int(correct) - 1]
        if correct not in options:
            continue

        explanation = _sanitize_explanation(
            row.get("explanation") or "",
            correct_answer=correct,
            force_example=True,
            question_text=question_text,
        )

        inferred_subject = _infer_subject_from_text(
            f"{question_text} {' '.join(options)} {explanation}"
        )
        if inferred_subject and inferred_subject != subject:
            continue

        normalized.append(
            {
                "question_text": question_text,
                "options": options,
                "correct_answer": correct,
                "explanation": explanation,
                "topic": _sanitize_text(row.get("topic") or topic or "NEET Practice"),
                "difficulty": difficulty,
            }
        )

    return normalized

def _generate_questions_vectorstore(subject, difficulty, count, topic, language):
    # First preference: real parsed NEET previous-year questions.
    seed_questions = _sample_neet_bank_questions(
        subject=subject,
        difficulty=str(difficulty),
        count=count,
        topic=topic,
    )
    if len(seed_questions) >= count:
        return seed_questions[:count]

    remaining = max(0, count - len(seed_questions))
    question_bank = get_vectorstore("question_bank")
    if not question_bank or remaining == 0:
        return seed_questions

    try:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import PromptTemplate

        llm = get_creative_llm()
        topic_hint = f" on topic: {topic}" if topic else ""
        retriever = question_bank.as_retriever(search_kwargs={"k": max(remaining * 6, 12)})
        docs = retriever.invoke(f"NEET {subject} {difficulty} solved MCQ{topic_hint}")

        filtered_docs = [
            doc for doc in docs
            if _infer_subject_from_text(getattr(doc, "page_content", "") or "") in {subject, None}
        ]
        working_docs = filtered_docs or docs

        context_rows: list[str] = []
        for doc in working_docs[: max(remaining * 4, 8)]:
            text = _clean_inline_text(getattr(doc, "page_content", "") or "")
            if text:
                context_rows.append(text[:1400])
        context = "\n\n".join(context_rows)

        examples_block = "\n\n".join(
            [
                f"Example {idx}:\nQ: {item['question_text']}\n"
                f"Options: {item['options']}\n"
                f"Correct: {item['correct_answer']}\n"
                f"Explanation style: {item['explanation'][:260]}"
                for idx, item in enumerate(seed_questions[:2], start=1)
            ]
        )

        difficulty_rubric = {
            "easy": "direct NCERT concept recall, minimal multi-step computation",
            "medium": "application-oriented with one to two logical steps",
            "hard": "multi-step NEET-level reasoning or numerical solving",
            "mixed": "balanced mix of easy, medium, and hard",
        }

        prompt = PromptTemplate.from_template(
            "You are a NEET-UG question setter and evaluator.\n"
            "Generate {count} NEW MCQs for {subject} at {difficulty} difficulty{topic_hint}.\n"
            "Difficulty rubric: {difficulty_rubric}.\n"
            "Do not copy the examples verbatim; match their NEET style and rigor.\n\n"
            "Seed examples:\n{examples_block}\n\n"
            "Context:\n{context}\n\n"
            "Write question_text, options, and explanation in {language_name}.\n"
            "Return ONLY a JSON array. Each object must have: "
            "question_text (string), options (array of 4 strings), "
            "correct_answer (one of the options verbatim), topic (string), and explanation (string).\n"
            "In explanation include:\n"
            "- 1) Why the selected option is correct\n"
            "- 2) One quick worked example prefixed with 'Example:'\n\n"
            "JSON:"
        )
        chain = prompt | llm | StrOutputParser()
        raw = chain.invoke(
            {
                "count": remaining,
                "subject": subject,
                "difficulty": difficulty,
                "topic_hint": topic_hint,
                "context": context,
                "difficulty_rubric": difficulty_rubric.get(str(difficulty).lower(), difficulty_rubric["medium"]),
                "examples_block": examples_block or "No examples available.",
                "language_name": language_name(language),
            }
        )
        # Strip markdown fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?", "", raw)
            raw = raw.rsplit("```", 1)[0].strip()

        generated = _coerce_generated_questions(
            raw_items=json.loads(raw),
            subject=subject,
            difficulty=str(difficulty),
            topic=topic,
        )
        return (seed_questions + generated)[:count]
    except Exception as exc:
        logger.warning(f"Vectorstore quiz generation failed: {exc}")
        return seed_questions


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
            "question_text": _sanitize_text(q[0]),
            "options": [_sanitize_text(option) for option in q[1]],
            "correct_answer": _sanitize_text(q[2]),
            "explanation": _sanitize_explanation(
                f"{q[3]}\n\nExample: Try changing one condition in the question and apply the same concept again.",
                correct_answer=_sanitize_text(q[2]),
                force_example=True,
                question_text=_sanitize_text(q[0]),
            ),
            "topic": _sanitize_text(topic or ""),
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


def _format_options_for_prompt(options: list[str] | None) -> str:
    cleaned_options = [_sanitize_text(option) for option in (options or []) if _sanitize_text(option)]
    if not cleaned_options:
        return "Not provided"
    return "\n".join(f"{idx + 1}. {option}" for idx, option in enumerate(cleaned_options[:6]))


async def _generate_dynamic_example_text(
    *,
    question: QuizQuestion,
    user_answer: str,
    is_correct: bool,
    selected_language_name: str,
) -> str | None:
    try:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import PromptTemplate

        llm = get_llm()
        prompt = PromptTemplate.from_template(
            "You are a NEET tutor. Create ONE fresh, concrete micro-example for this question.\n"
            "Question: {question}\n"
            "Options:\n{options}\n"
            "Learner answer: {user_answer}\n"
            "Correct answer: {correct_answer}\n"
            "Learner status: {verdict}\n"
            "Language: {language_name}\n\n"
            "Rules:\n"
            "- Write only example content (no 'Reason:' or 'Example:' labels).\n"
            "- 1-3 sentences, max 45 words.\n"
            "- Change a value/condition/context from the original question and show the resulting outcome.\n"
            "- Avoid stock phrases like 'apply the same concept', 'similar variant', or 'replace one value'.\n"
            "- Keep it specific, not generic.\n"
        )

        chain = prompt | llm | StrOutputParser()
        generated = await asyncio.wait_for(
            asyncio.to_thread(
                chain.invoke,
                {
                    "question": question.question_text,
                    "options": _format_options_for_prompt(question.options or []),
                    "user_answer": _sanitize_text(user_answer),
                    "correct_answer": _sanitize_text(question.correct_answer),
                    "verdict": "correct" if is_correct else "incorrect",
                    "language_name": selected_language_name,
                },
            ),
            timeout=QUIZ_DYNAMIC_EXAMPLE_TIMEOUT_SEC,
        )

        cleaned = re.sub(r"^\s*example\s*:\s*", "", _sanitize_text(generated), flags=re.I)
        if _is_dynamic_example_usable(cleaned):
            return cleaned
    except Exception as exc:
        logger.debug("Dynamic example generation skipped for question %s: %s", question.id, exc)

    return None


async def _attach_dynamic_example(
    *,
    explanation: str,
    question: QuizQuestion,
    user_answer: str,
    is_correct: bool,
    selected_language_name: str,
) -> str:
    reason_part, example_part = _split_reason_and_example(explanation)
    if not reason_part:
        reason_part = _stem_snippet(question.question_text)

    dynamic_example = await _generate_dynamic_example_text(
        question=question,
        user_answer=user_answer,
        is_correct=is_correct,
        selected_language_name=selected_language_name,
    )
    if dynamic_example:
        return _compose_explanation(reason_part, dynamic_example)

    if not example_part or _looks_generic_example(example_part):
        fallback_example = _example_hint_from_question(
            question.question_text,
            question.correct_answer,
            user_answer=user_answer,
            is_correct=is_correct,
        )
        return _compose_explanation(reason_part, fallback_example)

    return _compose_explanation(reason_part, example_part)


async def _build_answer_explanation(
    *,
    question: QuizQuestion,
    user_answer: str,
    is_correct: bool,
    request_language: str | None,
    language_header: str | None,
    user_preference: str | None,
) -> str:
    selected_language = resolve_request_language(
        explicit=request_language,
        header=language_header,
        user_preference=user_preference,
    )
    selected_language_name = language_name(selected_language)

    explanation = _sanitize_explanation(
        question.explanation or "",
        correct_answer=question.correct_answer,
        force_example=True,
        allow_fallback=False,
        question_text=question.question_text,
        user_answer=user_answer,
        is_correct=is_correct,
    )
    if _is_explanation_usable(explanation):
        return await _attach_dynamic_example(
            explanation=explanation,
            question=question,
            user_answer=user_answer,
            is_correct=is_correct,
            selected_language_name=selected_language_name,
        )

    try:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import PromptTemplate

        llm = get_llm()

        prompt = PromptTemplate.from_template(
            "You are an expert NEET tutor. Write a specific answer explanation.\n"
            "Question: {question}\n"
            "Options:\n{options}\n"
            "Learner answer: {user_answer}\n"
            "Correct answer: {correct_answer}\n"
            "Learner status: {verdict}\n"
            "Language: {language_name}\n\n"
            "Output exactly in this format:\n"
            "Reason: <2-4 concise sentences. Mention the key formula/concept and, if learner is incorrect, why their option fails. Avoid generic wording.>\n"
            "Example: <one short worked variant with one changed value/condition and final answer.>"
        )
        explanation_chain = prompt | llm | StrOutputParser()
        explanation = await asyncio.wait_for(
            asyncio.to_thread(
                explanation_chain.invoke,
                {
                    "question": question.question_text,
                    "options": _format_options_for_prompt(question.options or []),
                    "user_answer": _sanitize_text(user_answer),
                    "correct_answer": question.correct_answer,
                    "verdict": "correct" if is_correct else "incorrect",
                    "language_name": selected_language_name,
                },
            ),
            timeout=QUIZ_EXPLANATION_TIMEOUT_SEC,
        )
        explanation = _sanitize_explanation(
            explanation,
            correct_answer=question.correct_answer,
            force_example=True,
            allow_fallback=False,
            question_text=question.question_text,
            user_answer=user_answer,
            is_correct=is_correct,
        )
        if _is_explanation_usable(explanation):
            return await _attach_dynamic_example(
                explanation=explanation,
                question=question,
                user_answer=user_answer,
                is_correct=is_correct,
                selected_language_name=selected_language_name,
            )
    except asyncio.TimeoutError:
        logger.warning("Quiz explanation generation timed out for question %s", question.id)
    except Exception as exc:
        logger.warning("Quiz explanation generation failed for question %s: %s", question.id, exc)

    fallback_explanation = _fallback_explanation(
        question.correct_answer,
        question_text=question.question_text,
        user_answer=user_answer,
        is_correct=is_correct,
    )
    return await _attach_dynamic_example(
        explanation=fallback_explanation,
        question=question,
        user_answer=user_answer,
        is_correct=is_correct,
        selected_language_name=selected_language_name,
    )


# ---------------------------------------------------------------------------
# POST /api/quiz  — start quiz
# ---------------------------------------------------------------------------

@router.post("", response_model=StartQuizResponse, status_code=status.HTTP_201_CREATED)
async def start_quiz(
    request: StartQuizRequest,
    http_request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    subject = request.subject.value
    difficulty = request.difficulty
    count = request.question_count
    topic = request.topic
    selected_language = resolve_request_language(
        explicit=request.language,
        header=http_request.headers.get("X-APXMIND-Language"),
        user_preference=user.preferred_language,
    )

    # Generate questions with timeout guard so request does not stall on slow LLMs.
    try:
        raw_qs = await asyncio.wait_for(
            asyncio.to_thread(
                _generate_questions_vectorstore,
                subject,
                difficulty,
                count,
                topic,
                selected_language,
            ),
            timeout=QUIZ_GENERATION_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        logger.warning("Quiz generation timed out; using sample question fallback")
        raw_qs = []

    if not raw_qs:
        raw_qs = _generate_sample_questions(subject, difficulty, count, topic)

    if len(raw_qs) < count:
        top_up = _sample_neet_bank_questions(
            subject=subject,
            difficulty=str(difficulty),
            count=count - len(raw_qs),
            topic=topic,
        )
        existing = {_sanitize_text(item.get("question_text", "")).lower() for item in raw_qs}
        for item in top_up:
            key = _sanitize_text(item.get("question_text", "")).lower()
            if key and key not in existing:
                raw_qs.append(item)
                existing.add(key)
            if len(raw_qs) >= count:
                break

    if len(raw_qs) < count:
        raw_qs.extend(_generate_sample_questions(subject, difficulty, count - len(raw_qs), topic))

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
        question_text = _sanitize_text(q.get("question_text") or q.get("question", ""))
        options = [_sanitize_text(option) for option in q.get("options", [])]
        correct_answer = _sanitize_text(q.get("correct_answer", ""))
        if re.fullmatch(r"[1-4]", correct_answer) and 0 < int(correct_answer) <= len(options):
            correct_answer = options[int(correct_answer) - 1]
        if correct_answer not in options and options:
            keyed = {_sanitize_text(option).lower(): option for option in options}
            correct_answer = keyed.get(_sanitize_text(correct_answer).lower(), options[0])

        explanation = _sanitize_explanation(
            q.get("explanation", ""),
            correct_answer=correct_answer,
            force_example=True,
            question_text=question_text,
        )

        qq = QuizQuestion(
            quiz_id=quiz.id,
            question_no=i + 1,
            question_text=question_text,
            options=options,
            correct_answer=correct_answer,
            explanation=explanation,
            topic=_sanitize_text(q.get("topic", topic or "")),
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
    topic: str = Query(default=None),
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
    if topic and topic.strip():
        topic_query = topic.strip().lower()
        filters.append(func.lower(func.coalesce(Quiz.topic, "")).like(f"%{topic_query}%"))

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
# GET /api/quiz/question-bank/stats
# ---------------------------------------------------------------------------

@router.get("/question-bank/stats")
async def get_question_bank_stats(
    refresh: bool = Query(default=False),
    user: User = Depends(get_current_user),
):
    del user
    if refresh:
        _load_question_bank_mcqs.cache_clear()

    bank = _load_question_bank_mcqs()
    subjects = ("physics", "chemistry", "biology")
    difficulties = ("easy", "medium", "hard")

    subject_stats: dict[str, dict[str, Any]] = {}
    for subject in subjects:
        subset = [item for item in bank if item.get("subject") == subject]
        difficulty_counts = {
            level: sum(1 for row in subset if row.get("difficulty") == level)
            for level in difficulties
        }
        noisy_count = sum(
            1
            for row in subset
            if not _is_explanation_usable(
                _sanitize_explanation(
                    row.get("explanation", ""),
                    force_example=False,
                    allow_fallback=False,
                    question_text=row.get("question_text", ""),
                )
            )
        )
        subject_stats[subject] = {
            "total": len(subset),
            "difficulty": difficulty_counts,
            "explanation_low_quality": noisy_count,
        }

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_questions": len(bank),
        "subjects": subject_stats,
    }


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
    http_request: Request,
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

    user_answer_normalized = _sanitize_text(request.user_answer).lower()
    correct_answer_normalized = _sanitize_text(question.correct_answer).lower()
    is_correct = user_answer_normalized == correct_answer_normalized
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

    explanation = await _build_answer_explanation(
        question=question,
        user_answer=request.user_answer,
        is_correct=is_correct,
        request_language=request.language,
        language_header=http_request.headers.get("X-APXMIND-Language"),
        user_preference=user.preferred_language,
    )

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
    http_request: Request,
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

    explanation = await _build_answer_explanation(
        question=question,
        user_answer=request.user_answer,
        is_correct=is_correct,
        request_language=request.language,
        language_header=http_request.headers.get("X-APXMIND-Language"),
        user_preference=user.preferred_language,
    )

    return SubmitAnswerResponse(
        result=SubmitAnswerOut(
            is_correct=is_correct,
            correct_answer=question.correct_answer,
            explanation=explanation,
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
            explanation=_sanitize_explanation(
                q.explanation or "",
                correct_answer=q.correct_answer,
                force_example=True,
                question_text=q.question_text,
                user_answer=ans_map[q.id].user_answer if q.id in ans_map else "",
                is_correct=ans_map[q.id].is_correct if q.id in ans_map else None,
            ),
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
