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

from fastapi import APIRouter, HTTPException

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

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/generate-quiz",
    response_model=QuizResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Generate MCQ quiz",
)
async def generate_quiz(request: QuizRequest):
    """Generate a quiz with MCQ questions for the given subject and difficulty."""
    start_time = time.time()

    try:
        subject = request.subject.value
        difficulty = request.difficulty.value
        question_count = request.question_count

        logger.info(f"Generating quiz: subject={subject}, difficulty={difficulty}, count={question_count}")

        # Try vectorstore-based generation
        question_bank = get_vectorstore("question_bank")
        questions = []

        if question_bank:
            try:
                questions = _generate_quiz_from_vectorstore(
                    question_bank, subject, difficulty, question_count, request.topics
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
async def submit_answer(request: AnswerSubmitRequest):
    """Evaluate a user's answer to a quiz question."""
    try:
        is_correct = (
            request.user_answer.strip().upper() == request.correct_answer.strip().upper()
            if request.correct_answer
            else False
        )

        explanation = ""
        if request.question_text:
            try:
                llm = get_llm()
                from langchain_core.prompts import PromptTemplate
                from langchain_core.output_parsers import StrOutputParser

                prompt = PromptTemplate.from_template(
                    "Briefly explain why the answer to this NEET question is correct:\n\n"
                    "Question: {question}\nCorrect Answer: {answer}\n\nExplanation:"
                )
                chain = prompt | llm | StrOutputParser()
                explanation = chain.invoke({
                    "question": request.question_text,
                    "answer": request.correct_answer or request.user_answer,
                })
            except Exception as e:
                logger.warning(f"Explanation generation failed: {e}")
                explanation = "Explanation not available."

        return AnswerSubmitResponse(
            success=True,
            evaluation=AnswerEvaluation(
                correct=is_correct,
                correct_answer=request.correct_answer or "",
                explanation=explanation,
            ),
        )
    except Exception as e:
        logger.error(f"Answer evaluation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Helper functions ────────────────────────────────────────────────────────


def _generate_quiz_from_vectorstore(question_bank, subject, difficulty, count, topics):
    """Generate quiz questions using vectorstore retrieval + LLM."""
    from langchain_core.prompts import PromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    import json

    llm = get_creative_llm()

    topic_hint = f" on topics: {', '.join(topics)}" if topics else ""
    retriever = question_bank.as_retriever(search_kwargs={"k": count * 2})
    docs = retriever.invoke(f"{subject} {difficulty} NEET questions{topic_hint}")

    context = "\n\n".join(doc.page_content for doc in docs[:count * 2])

    prompt = PromptTemplate.from_template(
        "Based on the following NEET exam content, generate {count} multiple-choice questions "
        "for {subject} at {difficulty} difficulty.\n\n"
        "Context:\n{context}\n\n"
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
