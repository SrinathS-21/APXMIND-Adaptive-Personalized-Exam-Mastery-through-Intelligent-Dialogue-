"""
Trainer Router
===============

POST /api/trainer/generate-quiz — generate MCQ quiz
POST /api/trainer/submit-answer — evaluate user's answer
"""

import time
import uuid
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from ...api.schemas import (
    QuizRequest,
    QuizResponse,
    QuizData,
    QuizQuestion,
    AnswerSubmitRequest,
    AnswerSubmitResponse,
    AnswerEvaluation,
    ErrorResponse,
)
from ...core.dependencies import get_vectorstore, get_creative_llm, get_llm
from ...core.language import language_name, resolve_request_language

logger = logging.getLogger(__name__)

router = APIRouter()


def _normalize_answer(value: str) -> str:
    return (value or "").strip().lower()


def _choice_letter(value: str) -> str | None:
    token = (value or "").strip().upper()
    if len(token) == 1 and token in {"A", "B", "C", "D"}:
        return token
    return None


def _resolve_correct_answer_text(correct_answer: str | None, options: list[str] | None) -> str:
    if not correct_answer:
        return ""
    letter = _choice_letter(correct_answer)
    if letter and options:
        idx = ord(letter) - ord("A")
        if 0 <= idx < len(options):
            return options[idx]
    return correct_answer


def _build_fallback_explanation(
    *,
    question_text: str | None,
    is_correct: bool,
    user_answer: str,
    correct_answer_text: str,
) -> str:
    if is_correct:
        if correct_answer_text:
            return (
                f"Correct. The right answer is {correct_answer_text}. "
                "This option best matches the concept tested in the question."
            )
        return "Correct. Your selected option matches the expected answer for this question."

    if correct_answer_text:
        if user_answer:
            return (
                f"Incorrect. You selected {user_answer}, but the correct answer is "
                f"{correct_answer_text}. Review the core concept and keyword clues in the question."
            )
        return (
            f"Incorrect. The correct answer is {correct_answer_text}. "
            "Review the core concept and keyword clues in the question."
        )

    if question_text:
        return "Incorrect. Re-read the question stem and compare each option against the main concept being tested."
    return "Incorrect. Re-check the concept and compare all options carefully."


def _evaluate_answer(user_answer: str, correct_answer: str | None, options: list[str] | None) -> bool:
    if not correct_answer:
        return False

    user_norm = _normalize_answer(user_answer)
    correct_norm = _normalize_answer(correct_answer)

    # Direct text match path.
    if user_norm == correct_norm:
        return True

    user_letter = _choice_letter(user_answer)
    correct_letter = _choice_letter(correct_answer)

    # Letter-vs-letter path.
    if user_letter and correct_letter and user_letter == correct_letter:
        return True

    if not options:
        return False

    # Convert user text to option letter when possible.
    user_from_option_letter = None
    for idx, option in enumerate(options):
        if _normalize_answer(option) == user_norm:
            user_from_option_letter = chr(ord("A") + idx)
            break

    # Convert correct text to option letter when possible.
    correct_from_option_letter = None
    if not correct_letter:
        for idx, option in enumerate(options):
            if _normalize_answer(option) == correct_norm:
                correct_from_option_letter = chr(ord("A") + idx)
                break

    effective_user_letter = user_letter or user_from_option_letter
    effective_correct_letter = correct_letter or correct_from_option_letter
    if effective_user_letter and effective_correct_letter:
        return effective_user_letter == effective_correct_letter

    # Fallback text match against resolved correct option text.
    resolved_correct_text = _resolve_correct_answer_text(correct_answer, options)
    return bool(resolved_correct_text) and user_norm == _normalize_answer(resolved_correct_text)


@router.post(
    "/generate-quiz",
    response_model=QuizResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Generate MCQ quiz",
)
async def generate_quiz(request: QuizRequest, http_request: Request):
    """Generate a quiz with MCQ questions for the given subject and difficulty."""
    start_time = time.time()

    try:
        subject = request.subject.value
        difficulty = request.difficulty.value
        question_count = request.question_count
        selected_language = resolve_request_language(
            explicit=request.language,
            header=http_request.headers.get("X-APXMIND-Language"),
        )

        logger.info(f"Generating quiz: subject={subject}, difficulty={difficulty}, count={question_count}")

        # Try vectorstore-based generation
        question_bank = get_vectorstore("question_bank")
        questions = []

        if question_bank:
            try:
                questions = _generate_quiz_from_vectorstore(
                    question_bank,
                    subject,
                    difficulty,
                    question_count,
                    request.topics,
                    selected_language,
                )
            except Exception as e:
                logger.warning(f"Vectorstore quiz generation failed: {e}")

        if not questions:
            questions = _generate_sample_quiz(subject, difficulty, question_count)

        quiz_id = str(uuid.uuid4())
        time_limit = question_count * 60

        return QuizResponse(
            success=True,
            quiz=QuizData(
                quiz_id=quiz_id,
                subject=subject,
                difficulty=difficulty,
                questions=questions,
                total_questions=len(questions),
                time_limit=time_limit,
                created_at=datetime.utcnow().isoformat(),
            ),
            metadata={"generation_time_ms": round((time.time() - start_time) * 1000, 2)},
        )
    except Exception as e:
        logger.error(f"Quiz generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate quiz: {str(e)}")


@router.post(
    "/submit-answer",
    response_model=AnswerSubmitResponse,
    summary="Evaluate user's answer",
)
async def submit_answer(request: AnswerSubmitRequest, http_request: Request):
    """Evaluate a user's answer to a quiz question."""
    try:
        is_correct = _evaluate_answer(
            user_answer=request.user_answer,
            correct_answer=request.correct_answer,
            options=request.options,
        )

        resolved_correct_answer = _resolve_correct_answer_text(
            correct_answer=request.correct_answer,
            options=request.options,
        ) or (request.correct_answer or "")

        explanation = ""
        selected_language = resolve_request_language(
            explicit=request.language,
            header=http_request.headers.get("X-APXMIND-Language"),
        )
        selected_language_name = language_name(selected_language)
        if request.question_text:
            try:
                llm = get_llm()
                from langchain_core.prompts import PromptTemplate
                from langchain_core.output_parsers import StrOutputParser

                prompt = PromptTemplate.from_template(
                    "Briefly explain why the answer to this NEET question is correct:\n\n"
                    "Question: {question}\nCorrect Answer: {answer}\n"
                    "Write the explanation in {language_name}.\n\nExplanation:"
                )
                chain = prompt | llm | StrOutputParser()
                explanation = chain.invoke({
                    "question": request.question_text,
                    "answer": resolved_correct_answer or request.user_answer,
                    "language_name": selected_language_name,
                })
            except Exception as e:
                logger.warning(f"Explanation generation failed: {e}")

        if not explanation or not explanation.strip() or explanation.strip().lower() == "explanation not available.":
            explanation = _build_fallback_explanation(
                question_text=request.question_text,
                is_correct=is_correct,
                user_answer=request.user_answer,
                correct_answer_text=resolved_correct_answer,
            )

        return AnswerSubmitResponse(
            success=True,
            evaluation=AnswerEvaluation(
                correct=is_correct,
                correct_answer=resolved_correct_answer,
                explanation=explanation,
            ),
        )
    except Exception as e:
        logger.error(f"Answer evaluation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Helper functions ────────────────────────────────────────────────────────


def _generate_quiz_from_vectorstore(question_bank, subject, difficulty, count, topics, language):
    """Generate quiz questions using vectorstore retrieval + LLM."""
    from langchain_core.prompts import PromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    import json

    llm = get_creative_llm()
    output_language_name = language_name(language)

    topic_hint = f" on topics: {', '.join(topics)}" if topics else ""
    retriever = question_bank.as_retriever(search_kwargs={"k": count * 2})
    docs = retriever.invoke(f"{subject} {difficulty} NEET questions{topic_hint}")

    context = "\n\n".join(doc.page_content for doc in docs[:count * 2])

    prompt = PromptTemplate.from_template(
        "Based on the following NEET exam content, generate {count} multiple-choice questions "
        "for {subject} at {difficulty} difficulty.\n\n"
        "Context:\n{context}\n\n"
        "Write question text, options, and explanations in {language_name}.\n"
        "Return ONLY a JSON array of objects with keys: question, options (array of 4), "
        "correct_answer (letter A-D), explanation, topic.\n\n"
        "JSON:"
    )
    chain = prompt | llm | StrOutputParser()
    raw = chain.invoke({
        "count": count,
        "subject": subject,
        "difficulty": difficulty,
        "context": context,
        "language_name": output_language_name,
    })

    try:
        parsed = json.loads(raw)
        return [
            QuizQuestion(
                id=i + 1,
                question=q.get("question", ""),
                options=q.get("options", []),
                correct_answer=q.get("correct_answer", ""),
                explanation=q.get("explanation", ""),
                difficulty=difficulty,
                topic=q.get("topic", ""),
            )
            for i, q in enumerate(parsed[:count])
        ]
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM quiz output as JSON")
        return []


def _generate_sample_quiz(subject, difficulty, count):
    """Generate placeholder sample questions as fallback."""
    samples = {
        "biology": [
            ("What is the powerhouse of the cell?", ["Nucleus", "Mitochondria", "Ribosome", "Golgi body"], "B"),
            ("Which organelle is responsible for photosynthesis?", ["Mitochondria", "Chloroplast", "Nucleus", "ER"], "B"),
            ("DNA replication occurs in which phase?", ["G1", "S", "G2", "M"], "B"),
            ("Which vitamin is produced by skin in sunlight?", ["Vitamin A", "Vitamin B", "Vitamin C", "Vitamin D"], "D"),
            ("The largest organ of the human body is?", ["Liver", "Skin", "Brain", "Heart"], "B"),
        ],
        "chemistry": [
            ("What is the atomic number of Carbon?", ["4", "6", "8", "12"], "B"),
            ("Which gas is most abundant in Earth's atmosphere?", ["Oxygen", "Nitrogen", "CO2", "Argon"], "B"),
            ("pH of pure water at 25°C is?", ["6", "7", "8", "14"], "B"),
            ("Which element has the highest electronegativity?", ["Oxygen", "Chlorine", "Fluorine", "Nitrogen"], "C"),
            ("Avogadro's number is approximately?", ["6.02×10²²", "6.02×10²³", "6.02×10²⁴", "3.14×10²³"], "B"),
        ],
        "physics": [
            ("What is the SI unit of force?", ["Joule", "Newton", "Watt", "Pascal"], "B"),
            ("Speed of light in vacuum is?", ["3×10⁶ m/s", "3×10⁸ m/s", "3×10¹⁰ m/s", "3×10⁴ m/s"], "B"),
            ("Which law states F=ma?", ["First", "Second", "Third", "Zeroth"], "B"),
            ("Unit of electric current is?", ["Volt", "Ohm", "Ampere", "Watt"], "C"),
            ("Acceleration due to gravity is approximately?", ["8.9 m/s²", "9.8 m/s²", "10.8 m/s²", "11.2 m/s²"], "B"),
        ],
    }

    questions = samples.get(subject, samples["biology"])[:count]
    return [
        QuizQuestion(
            id=i + 1,
            question=q[0],
            options=q[1],
            correct_answer=q[2],
            explanation="",
            difficulty=difficulty,
            topic="",
        )
        for i, q in enumerate(questions)
    ]
