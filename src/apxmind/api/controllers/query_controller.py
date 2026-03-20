"""
Query Controller
================

Handles intelligent query processing using the 3-tier architecture:
- Tier-0: Intent classification and routing
- Tier-1: Retrieval-based QA (RAG)
- Tier-2: Advanced multi-agent orchestration

Endpoint: POST /api/query
"""

import time
from flask import jsonify, request, current_app
from datetime import datetime


def process_query():
    """
    Process user query through the 3-tier intelligence system.
    
    Request Body:
        {
            "query": "What is photosynthesis?",
            "subject": "biology",  // optional
            "user_id": 1,  // optional
            "context": {}  // optional context
        }
    
    Response:
        {
            "success": true,
            "answer": "Photosynthesis is...",
            "metadata": {
                "tier": "tier1",
                "agent": "retriever",
                "confidence": 0.95,
                "sources": [...],
                "latency_ms": 1234
            }
        }
    
    Returns:
        JSON response with answer and metadata
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
        
        query = data.get('query', '').strip()
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query is required'
            }), 400
        
        subject = data.get('subject', '').lower()
        user_id = data.get('user_id')
        context = data.get('context', {})
        
        current_app.logger.info(f"Processing query: {query[:100]}... (subject: {subject or 'auto'})")
        
        # Import intelligence components (lazy import to avoid circular dependency)
        from src.apxmind.api.agents import classify_intent, retriever_agent, orchestrator_agent
        from src.apxmind.core.resources import get_vectorstore, get_llm
        
        # TIER-0: Classify intent
        tier0_start = time.time()
        intent_result = classify_intent(query, subject)
        tier0_latency = (time.time() - tier0_start) * 1000
        
        current_app.logger.info(f"Tier-0 classification: {intent_result['intent']} (confidence: {intent_result.get('confidence', 0):.2f}, {tier0_latency:.0f}ms)")
        
        intent = intent_result.get('intent', 'complex')
        detected_subject = intent_result.get('subject', subject)
        
        # Route based on intent
        if intent == 'simple' or intent == 'retrieval':
            # TIER-1: Retrieval-based QA (RAG)
            tier1_start = time.time()
            
            # Get appropriate vectorstore
            vectorstore = get_vectorstore(detected_subject)
            llm = get_llm()
            
            # Run retriever agent
            result = retriever_agent(
                query=query,
                vectorstore=vectorstore,
                llm=llm,
                subject=detected_subject
            )
            
            tier1_latency = (time.time() - tier1_start) * 1000
            
            response = {
                'success': True,
                'answer': result.get('answer', ''),
                'metadata': {
                    'tier': 'tier1',
                    'agent': 'retriever',
                    'intent': intent,
                    'subject': detected_subject,
                    'confidence': result.get('confidence', 0.0),
                    'sources': result.get('sources', []),
                    'tier0_latency_ms': round(tier0_latency, 2),
                    'tier1_latency_ms': round(tier1_latency, 2),
                    'total_latency_ms': round((time.time() - start_time) * 1000, 2),
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
            
            current_app.logger.info(f"Tier-1 completed: {tier1_latency:.0f}ms, total: {response['metadata']['total_latency_ms']:.0f}ms")
            
        else:
            # TIER-2: Advanced orchestration for complex queries
            tier2_start = time.time()
            
            llm = get_llm()
            vectorstores = {
                'biology': get_vectorstore('biology'),
                'chemistry': get_vectorstore('chemistry'),
                'physics': get_vectorstore('physics')
            }
            
            # Run orchestrator agent
            result = orchestrator_agent(
                query=query,
                vectorstores=vectorstores,
                llm=llm,
                subject=detected_subject
            )
            
            tier2_latency = (time.time() - tier2_start) * 1000
            
            response = {
                'success': True,
                'answer': result.get('answer', ''),
                'metadata': {
                    'tier': 'tier2',
                    'agent': 'orchestrator',
                    'intent': intent,
                    'subject': detected_subject,
                    'confidence': result.get('confidence', 0.0),
                    'sources': result.get('sources', []),
                    'reasoning': result.get('reasoning', ''),
                    'tier0_latency_ms': round(tier0_latency, 2),
                    'tier2_latency_ms': round(tier2_latency, 2),
                    'total_latency_ms': round((time.time() - start_time) * 1000, 2),
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
            
            current_app.logger.info(f"Tier-2 completed: {tier2_latency:.0f}ms, total: {response['metadata']['total_latency_ms']:.0f}ms")
        
        # Log performance warning if too slow
        total_latency = response['metadata']['total_latency_ms']
        if total_latency > 1500:
            current_app.logger.warning(f"Query latency exceeded target: {total_latency:.0f}ms > 1500ms")
        
        return jsonify(response), 200
        
    except Exception as e:
        # Comprehensive error handling
        latency = (time.time() - start_time) * 1000
        current_app.logger.error(f"Query processing failed after {latency:.0f}ms: {str(e)}", exc_info=True)
        
        # Provide user-friendly error response
        return jsonify({
            'success': False,
            'error': 'Failed to process query. Please try again.',
            'details': str(e) if current_app.config.get('DEBUG') else None,
            'metadata': {
                'latency_ms': round(latency, 2),
                'timestamp': datetime.utcnow().isoformat()
            }
        }), 500


def get_query_history(user_id):
    """
    Get query history for a user.
    
    Args:
        user_id: User ID
    
    Returns:
        JSON list of previous queries
    """
    try:
        # TODO: Implement query history tracking in database
        # For now, return empty list
        return jsonify({
            'success': True,
            'queries': [],
            'count': 0
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Failed to get query history: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
