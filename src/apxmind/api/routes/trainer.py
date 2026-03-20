"""
Trainer Routes
==============

API routes for quiz generation and answer evaluation.
"""

from flask import Blueprint
from src.apxmind.api.controllers import trainer_controller

# Create blueprint
trainer_bp = Blueprint('trainer', __name__, url_prefix='/api/trainer')


@trainer_bp.route('/generate-quiz', methods=['POST'])
def generate_quiz():
    """POST /api/trainer/generate-quiz - Generate MCQ quiz."""
    return trainer_controller.generate_quiz()


@trainer_bp.route('/submit-answer', methods=['POST'])
def submit_answer():
    """POST /api/trainer/submit-answer - Evaluate user's answer."""
    return trainer_controller.submit_answer()
