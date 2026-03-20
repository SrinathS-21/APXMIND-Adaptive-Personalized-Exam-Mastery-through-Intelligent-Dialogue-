"""
Subject Controller
==================

Handles subject-related endpoints:
- GET /api/subjects - List all subjects
- GET /api/subjects/:subject/lessons - List lessons for a subject
"""

from flask import jsonify, current_app
import sys
import os

# Add parent directory to path to import models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from models import Subject, Lesson


def get_all_subjects():
    """
    Get all NEET subjects.
    
    Returns:
        JSON list of all subjects with metadata
    """
    try:
        # Query using the properly initialized models
        subjects = Subject.query.all()
        
        return jsonify({
            'success': True,
            'data': [subject.to_dict() for subject in subjects],
            'count': len(subjects)
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error getting subjects: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def get_subject_lessons(subject_name):
    """
    Get all lessons for a specific subject.
    
    Args:
        subject_name: Name of the subject (biology, chemistry, or physics)
    
    Returns:
        JSON list of lessons for the subject
    """
    try:
        # Normalize subject name
        subject_name = subject_name.lower()
        
        # Find subject
        subject = Subject.query.filter_by(name=subject_name).first()
        if not subject:
            return jsonify({
                'success': False,
                'error': f'Subject not found: {subject_name}'
            }), 404
        
        # Get lessons
        lessons = Lesson.query.filter_by(subject_id=subject.id).order_by(Lesson.order).all()
        
        return jsonify({
            'success': True,
            'subject': subject.to_dict(),
            'lessons': [lesson.to_dict() for lesson in lessons],
            'count': len(lessons)
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error getting lessons for {subject_name}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
