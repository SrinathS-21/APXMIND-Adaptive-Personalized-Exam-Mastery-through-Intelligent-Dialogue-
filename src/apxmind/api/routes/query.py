"""
Query Routes
============

API routes for intelligent query processing.
"""

from flask import Blueprint
from src.apxmind.api.controllers import query_controller

# Create blueprint
query_bp = Blueprint('query', __name__, url_prefix='/api')


@query_bp.route('/query', methods=['POST'])
def process_query():
    """POST /api/query - Process user query through intelligence layer."""
    return query_controller.process_query()


@query_bp.route('/user/<int:user_id>/queries', methods=['GET'])
def get_query_history(user_id):
    """GET /api/user/:id/queries - Get query history for user."""
    return query_controller.get_query_history(user_id)
