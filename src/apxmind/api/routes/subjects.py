"""
Subject Routes
==============

API routes for subject and lesson endpoints.
"""

from flask import Blueprint
from src.apxmind.api.controllers import subject_controller

# Create blueprint
subjects_bp = Blueprint('subjects', __name__, url_prefix='/api/subjects')


@subjects_bp.route('', methods=['GET'])
@subjects_bp.route('/', methods=['GET'])
def get_subjects():
    """GET /api/subjects - List all subjects."""
    return subject_controller.get_all_subjects()


@subjects_bp.route('/<string:subject_name>/lessons', methods=['GET'])
def get_lessons(subject_name):
    """GET /api/subjects/:subject/lessons - Get lessons for a subject."""
    return subject_controller.get_subject_lessons(subject_name)
