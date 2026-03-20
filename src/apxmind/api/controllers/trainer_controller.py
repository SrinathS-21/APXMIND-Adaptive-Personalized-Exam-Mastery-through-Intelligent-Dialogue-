"""
Trainer Controller
==================

Handles quiz generation and answer evaluation endpoints:
- POST /api/trainer/generate-quiz - Generate MCQ quiz
- POST /api/trainer/submit-answer - Evaluate user's answer
"""

import time
import random
from flask import jsonify, request, current_app
from datetime import datetime
from typing import Dict, Any, List


def generate_quiz():
    """
    Generate a quiz with MCQ questions.
    
    Request Body:
        {
            "subject": "biology",  // required
            "difficulty": "medium",  // optional: easy, medium, hard
            "question_count": 5,  // optional: default 5
            "topics": ["photosynthesis"]  // optional: specific topics
        }
    
    Response:
        {
            "success": true,
            "quiz": {
                "quiz_id": "uuid",
                "subject": "biology",
                "difficulty": "medium",
                "questions": [...],
                "total_questions": 5,
                "time_limit": 300  // seconds
            }
        }
    
    Returns:
        JSON response with quiz questions
    """
    start_time = time.time()
    
    try:
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        subject = data.get('subject', '').lower()
        if not subject or subject not in ['biology', 'chemistry', 'physics']:
            return jsonify({
                'success': False,
                'error': 'Valid subject is required (biology, chemistry, or physics)'
            }), 400
        
        difficulty = data.get('difficulty', 'medium').lower()
        if difficulty not in ['easy', 'medium', 'hard']:
            difficulty = 'medium'
        
        question_count = min(max(data.get('question_count', 5), 1), 20)  # Limit to 1-20
        topics = data.get('topics', [])
        
        current_app.logger.info(f"Generating quiz: subject={subject}, difficulty={difficulty}, count={question_count}")
        
        # Try to generate quiz from question bank vectorstore
        try:
            from src.apxmind.core.resources import get_vectorstore, get_creative_llm
            
            question_bank = get_vectorstore('question_bank')
            
            if question_bank:
                # Generate quiz using retrieval and LLM
                questions = _generate_quiz_from_vectorstore(
                    question_bank=question_bank,
                    subject=subject,
                    difficulty=difficulty,
                    count=question_count,
                    topics=topics
                )
            else:
                # Fallback to sample questions
                questions = _generate_sample_quiz(subject, difficulty, question_count)
                
        except Exception as e:
            current_app.logger.warning(f"Quiz generation from vectorstore failed: {e}, using fallback")
            questions = _generate_sample_quiz(subject, difficulty, question_count)
        
        # Generate quiz ID
        import uuid
        quiz_id = str(uuid.uuid4())
        
        # Calculate time limit (1 minute per question)
        time_limit = question_count * 60
        
        response = {
            'success': True,
            'quiz': {
                'quiz_id': quiz_id,
                'subject': subject,
                'difficulty': difficulty,
                'questions': questions,
                'total_questions': len(questions),
                'time_limit': time_limit,
                'created_at': datetime.utcnow().isoformat()
            },
            'metadata': {
                'generation_time_ms': round((time.time() - start_time) * 1000, 2)
            }
        }
        
        current_app.logger.info(f"Quiz generated: {len(questions)} questions in {response['metadata']['generation_time_ms']:.0f}ms")
        
        return jsonify(response), 200
        
    except Exception as e:
        latency = (time.time() - start_time) * 1000
        current_app.logger.error(f"Quiz generation failed after {latency:.0f}ms: {str(e)}", exc_info=True)
        
        return jsonify({
            'success': False,
            'error': 'Failed to generate quiz. Please try again.',
            'details': str(e) if current_app.config.get('DEBUG') else None
        }), 500


def submit_answer():
    """
    Evaluate user's answer to a quiz question.
    
    Request Body:
        {
            "quiz_id": "uuid",
            "question_id": 1,
            "user_answer": "A",  // or answer text
            "question_text": "What is photosynthesis?",  // for context
            "correct_answer": "A"  // optional, if validating
        }
    
    Response:
        {
            "success": true,
            "evaluation": {
                "correct": true,
                "user_answer": "A",
                "correct_answer": "A",
                "explanation": "Photosynthesis is...",
                "score": 1
            }
        }
    
    Returns:
        JSON response with evaluation results
    """
    start_time = time.time()
    
    try:
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        quiz_id = data.get('quiz_id')
        question_id = data.get('question_id')
        user_answer = data.get('user_answer', '').strip()
        question_text = data.get('question_text', '')
        correct_answer = data.get('correct_answer', '').strip()
        
        if not user_answer:
            return jsonify({
                'success': False,
                'error': 'User answer is required'
            }), 400
        
        current_app.logger.info(f"Evaluating answer: quiz={quiz_id}, question={question_id}, answer={user_answer}")
        
        # Evaluate answer
        is_correct = False
        explanation = ""
        
        if correct_answer:
            # Simple comparison
            is_correct = user_answer.upper() == correct_answer.upper()
            
            if is_correct:
                explanation = "Correct! Well done."
            else:
                explanation = f"Incorrect. The correct answer is {correct_answer}."
        else:
            # Try to generate explanation using LLM (if available)
            try:
                from src.apxmind.core.resources import get_llm
                llm = get_llm()
                
                from langchain_core.prompts import PromptTemplate
                from langchain_core.output_parsers import StrOutputParser
                
                eval_template = """Evaluate this NEET exam answer and provide a brief explanation.

Question: {question}
Student's Answer: {user_answer}

Provide:
1. Whether the answer is correct (Yes/No)
2. A brief explanation

Response:"""
                
                eval_chain = PromptTemplate.from_template(eval_template) | llm | StrOutputParser()
                explanation = eval_chain.invoke({
                    "question": question_text,
                    "user_answer": user_answer
                })
                
                is_correct = "correct" in explanation.lower() or "yes" in explanation.lower()
                
            except Exception as e:
                current_app.logger.warning(f"LLM evaluation failed: {e}")
                explanation = "Answer submitted. Please check with your study materials."
        
        # Calculate score
        score = 1 if is_correct else 0
        
        response = {
            'success': True,
            'evaluation': {
                'correct': is_correct,
                'user_answer': user_answer,
                'correct_answer': correct_answer if correct_answer else None,
                'explanation': explanation,
                'score': score,
                'question_id': question_id,
                'quiz_id': quiz_id
            },
            'metadata': {
                'evaluation_time_ms': round((time.time() - start_time) * 1000, 2),
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        
        current_app.logger.info(f"Answer evaluated: correct={is_correct}, time={response['metadata']['evaluation_time_ms']:.0f}ms")
        
        return jsonify(response), 200
        
    except Exception as e:
        latency = (time.time() - start_time) * 1000
        current_app.logger.error(f"Answer evaluation failed after {latency:.0f}ms: {str(e)}", exc_info=True)
        
        return jsonify({
            'success': False,
            'error': 'Failed to evaluate answer. Please try again.',
            'details': str(e) if current_app.config.get('DEBUG') else None
        }), 500


def _generate_quiz_from_vectorstore(
    question_bank,
    subject: str,
    difficulty: str,
    count: int,
    topics: List[str]
) -> List[Dict[str, Any]]:
    """
    Generate quiz questions from vectorstore.
    
    Args:
        question_bank: Question bank vectorstore
        subject: Subject name
        difficulty: Difficulty level
        count: Number of questions
        topics: Optional list of topics
    
    Returns:
        List of question dictionaries
    """
    from src.apxmind.core.resources import get_creative_llm
    from langchain_core.prompts import PromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    
    try:
        # Build search query
        if topics:
            query = f"{subject} {difficulty} {' '.join(topics)}"
        else:
            query = f"{subject} {difficulty} NEET questions"
        
        # Retrieve questions from vectorstore
        retriever = question_bank.as_retriever(search_kwargs={"k": count * 2})
        retrieved_docs = retriever.invoke(query)
        
        if not retrieved_docs:
            raise Exception("No questions found in question bank")
        
        # Use LLM to format questions
        llm = get_creative_llm()
        
        questions = []
        for i, doc in enumerate(retrieved_docs[:count]):
            # Extract question from document
            question_text = doc.page_content
            
            # Format as MCQ (if not already)
            format_template = """Format this NEET question as a clear MCQ with 4 options (A, B, C, D).
If it's already formatted, return it as-is.

Question: {question}

Formatted MCQ:"""
            
            format_chain = PromptTemplate.from_template(format_template) | llm | StrOutputParser()
            formatted_question = format_chain.invoke({"question": question_text})
            
            questions.append({
                'question_id': i + 1,
                'question': formatted_question,
                'difficulty': difficulty,
                'topic': doc.metadata.get('topic', subject) if doc.metadata else subject
            })
        
        return questions
        
    except Exception as e:
        raise Exception(f"Failed to generate from vectorstore: {e}")


def _generate_sample_quiz(subject: str, difficulty: str, count: int) -> List[Dict[str, Any]]:
    """
    Generate sample quiz questions (fallback when vectorstore/LLM unavailable).
    
    Args:
        subject: Subject name
        difficulty: Difficulty level
        count: Number of questions
    
    Returns:
        List of sample question dictionaries
    """
    # Sample questions for each subject
    sample_questions = {
        'biology': [
            {
                'question': 'What is the powerhouse of the cell?\nA) Nucleus\nB) Mitochondria\nC) Ribosome\nD) Golgi apparatus',
                'answer': 'B',
                'topic': 'Cell Biology',
                'difficulty': 'easy'
            },
            {
                'question': 'Which process converts light energy into chemical energy?\nA) Respiration\nB) Digestion\nC) Photosynthesis\nD) Fermentation',
                'answer': 'C',
                'topic': 'Photosynthesis',
                'difficulty': 'easy'
            },
            {
                'question': 'What is the primary pigment in photosynthesis?\nA) Carotene\nB) Xanthophyll\nC) Chlorophyll\nD) Anthocyanin',
                'answer': 'C',
                'topic': 'Photosynthesis',
                'difficulty': 'medium'
            },
            {
                'question': 'In which part of the cell does the Krebs cycle occur?\nA) Cytoplasm\nB) Mitochondrial matrix\nC) Nucleus\nD) Endoplasmic reticulum',
                'answer': 'B',
                'topic': 'Respiration',
                'difficulty': 'medium'
            },
            {
                'question': 'What is the end product of glycolysis?\nA) Glucose\nB) Pyruvate\nC) ATP only\nD) CO2',
                'answer': 'B',
                'topic': 'Respiration',
                'difficulty': 'hard'
            }
        ],
        'chemistry': [
            {
                'question': 'What is the atomic number of Carbon?\nA) 6\nB) 12\nC) 8\nD) 14',
                'answer': 'A',
                'topic': 'Atomic Structure',
                'difficulty': 'easy'
            },
            {
                'question': 'Which type of bond is formed by sharing electrons?\nA) Ionic\nB) Covalent\nC) Metallic\nD) Hydrogen',
                'answer': 'B',
                'topic': 'Chemical Bonding',
                'difficulty': 'easy'
            },
            {
                'question': 'What is the molecular formula of glucose?\nA) C6H12O6\nB) C12H22O11\nC) CH4\nD) C2H5OH',
                'answer': 'A',
                'topic': 'Organic Chemistry',
                'difficulty': 'medium'
            },
            {
                'question': 'Which law states that energy cannot be created or destroyed?\nA) Boyle\'s Law\nB) First Law of Thermodynamics\nC) Law of Mass Action\nD) Hess\'s Law',
                'answer': 'B',
                'topic': 'Thermodynamics',
                'difficulty': 'medium'
            },
            {
                'question': 'What is the hybridization of carbon in methane (CH4)?\nA) sp\nB) sp2\nC) sp3\nD) sp3d',
                'answer': 'C',
                'topic': 'Chemical Bonding',
                'difficulty': 'hard'
            }
        ],
        'physics': [
            {
                'question': 'What is the SI unit of force?\nA) Joule\nB) Newton\nC) Watt\nD) Pascal',
                'answer': 'B',
                'topic': 'Mechanics',
                'difficulty': 'easy'
            },
            {
                'question': 'What is Newton\'s first law of motion?\nA) F = ma\nB) Law of inertia\nC) Action-reaction\nD) Conservation of energy',
                'answer': 'B',
                'topic': 'Laws of Motion',
                'difficulty': 'easy'
            },
            {
                'question': 'What is the kinetic energy formula?\nA) mgh\nB) 1/2 mv²\nC) Fd\nD) Pt',
                'answer': 'B',
                'topic': 'Work and Energy',
                'difficulty': 'medium'
            },
            {
                'question': 'What is Coulomb\'s constant approximately equal to?\nA) 9 × 10⁹ N⋅m²/C²\nB) 6.67 × 10⁻¹¹ N⋅m²/kg²\nC) 3 × 10⁸ m/s\nD) 6.63 × 10⁻³⁴ J⋅s',
                'answer': 'A',
                'topic': 'Electrostatics',
                'difficulty': 'medium'
            },
            {
                'question': 'In an elastic collision, which quantity is conserved?\nA) Kinetic energy only\nB) Momentum only\nC) Both kinetic energy and momentum\nD) Neither',
                'answer': 'C',
                'topic': 'Mechanics',
                'difficulty': 'hard'
            }
        ]
    }
    
    # Get questions for the subject
    subject_questions = sample_questions.get(subject, sample_questions['biology'])
    
    # Filter by difficulty if possible
    filtered_questions = [q for q in subject_questions if q['difficulty'] == difficulty]
    if not filtered_questions:
        filtered_questions = subject_questions
    
    # Randomly select questions
    selected = random.sample(filtered_questions, min(count, len(filtered_questions)))
    
    # Format questions
    questions = []
    for i, q in enumerate(selected):
        questions.append({
            'question_id': i + 1,
            'question': q['question'],
            'correct_answer': q['answer'],
            'difficulty': q['difficulty'],
            'topic': q['topic']
        })
    
    return questions
