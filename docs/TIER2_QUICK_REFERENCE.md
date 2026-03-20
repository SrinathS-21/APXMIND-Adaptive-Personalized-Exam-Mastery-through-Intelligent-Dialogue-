# Tier-2 Orchestrator: Quick Reference

**File:** `src/APXMIND/routing/tier2_orchestrator.py`  
**Status:** ✅ Production Ready  
**Version:** 2.0.0

---

## Quick Start

```python
from src.apxmind.routing import (
    Tier0Classifier,
    Tier1Retriever,
    Tier2Orchestrator,
    TeacherAgent,
    TrainerAgent,
    DoubtSolverAgent,
    MentorAgent,
    GeneralAgent,
    AgentType
)

# Initialize all components
tier0 = Tier0Classifier()
tier1 = Tier1Retriever(hybrid_retriever, chroma_manager)

# Create agents
agents = {
    AgentType.TEACHER: TeacherAgent(),
    AgentType.TRAINER: TrainerAgent(),
    AgentType.DOUBT_SOLVER: DoubtSolverAgent(),
    AgentType.MENTOR: MentorAgent(),
    AgentType.GENERAL: GeneralAgent()
}

# Initialize orchestrator
tier2 = Tier2Orchestrator(agents=agents, tier1_retriever=tier1)

# Complete pipeline
classification = tier0.classify_query(query, user_profile)
retrieval = await tier1.retrieve(classification, query)
response = await tier2.execute_agent(
    classification=classification,
    retrieved_docs=retrieval,
    query=query,
    user_profile=user_profile
)

# Use response
print(f"Agent: {response.metadata['agent_used']}")
print(f"Confidence: {response.metadata['confidence_score']}")
print(f"Response: {response.content['text']}")
```

---

## Agent Selection

| Intent | Agent | Strategy |
|--------|-------|----------|
| TEACH | TeacherAgent | C-RAG (uses retrieval) |
| TRAIN | TrainerAgent | Few-shot (uses examples) |
| DOUBT | DoubtSolverAgent | Zero-shot (reasoning) |
| MENTOR | MentorAgent | C-RAG (guidance docs) |
| GENERAL | GeneralAgent | Conversational |

---

## Context Validation

| Agent | Required Docs | Fallback if Insufficient |
|-------|---------------|--------------------------|
| Teacher | ≥1 relevant | Zero-shot LLM |
| Trainer | ≥3 relevant | Stage 2 → Zero-shot |
| Mentor | ≥2 relevant | Zero-shot LLM |
| Doubt Solver | 0 (none) | N/A |
| General | 0 (none) | N/A |

---

## Confidence Scores

| Method | Stage | Quality | Confidence |
|--------|-------|---------|------------|
| C-RAG | 0 | ≥0.85 | 0.94 |
| C-RAG | 1 | ≥0.70 | 0.87 |
| C-RAG | Any | 0.60-0.70 | 0.80 |
| Few-Shot | - | ≥0.80 | 0.90 |
| Few-Shot | - | <0.80 | 0.85 |
| Zero-Shot | - | N/A | 0.75 |
| Fallback | - | N/A | 0.70 |

---

## API Reference

### Tier2Orchestrator.execute_agent()

```python
async def execute_agent(
    classification: ClassificationResult,
    retrieved_docs: Tier1Result,
    query: str,
    user_profile: Dict[str, Any]
) -> AgentResponse
```

**Parameters:**
- `classification` - Tier-0 classification result
- `retrieved_docs` - Tier-1 retrieval result
- `query` - Original user query
- `user_profile` - User information

**Returns:**
- `AgentResponse` with content, metadata, enrichment, performance

### AgentResponse Structure

```python
{
    'success': bool,
    'content': {
        'text': str,              # Main response text
        'language': str,          # Response language
        'options': dict,          # For MCQs (TrainerAgent)
        'correct_answer': str,    # For MCQs
        'explanation': str        # For MCQs
    },
    'metadata': {
        'agent_used': str,            # Agent type
        'confidence_score': float,     # 0.0-1.0
        'retrieval_method': str,       # C-RAG/few-shot/zero-shot
        'retrieval_stage': int,        # 0 or 1
        'retrieval_sources': list,     # Document IDs
        'subject': str,                # Subject area
        'intent': str,                 # Query intent
        'difficulty': str,             # Difficulty level
        'focus_area': str              # Topic focus
    },
    'enrichment': {
        'learning_objectives': list,   # Learning goals
        'related_topics': list,        # Related areas
        'difficulty_feedback': str,    # Level feedback
        'next_steps': list             # Suggested actions
    },
    'performance': {
        'total_latency_ms': float,     # Total time
        'tier0_latency_ms': float,     # Classification time
        'tier1_latency_ms': float,     # Retrieval time
        'tier2_latency_ms': float,     # Orchestration time
        'agent_execution_ms': float    # Agent processing time
    }
}
```

---

## Common Patterns

### Pattern 1: Complete Pipeline

```python
# User query
query = "Explain Newton's Second Law"

# Step 1: Classify
classification = tier0.classify_query(query, user_profile)
# → subject=PHYSICS, intent=TEACH, focus="newtons_second_law"

# Step 2: Retrieve
retrieval = await tier1.retrieve(classification, query)
# → 3 docs, quality=0.92, stage=0

# Step 3: Orchestrate
response = await tier2.execute_agent(
    classification, retrieval, query, user_profile
)

# Result:
# - Agent: TeacherAgent (C-RAG)
# - Confidence: 0.94 (high quality retrieval)
# - Content: Detailed explanation with sources
```

### Pattern 2: Fallback Scenario

```python
# Insufficient context
query = "Generate practice questions on rare topic"

classification = tier0.classify_query(query, user_profile)
retrieval = await tier1.retrieve(classification, query)
# → Only 1 doc found (need 3 for trainer)

response = await tier2.execute_agent(
    classification, retrieval, query, user_profile
)

# Orchestrator detects insufficient context
# → Triggers fallback to zero-shot
# - Agent: TrainerAgent (zero-shot mode)
# - Confidence: 0.75 (lower, no examples)
# - Content: Question from LLM base knowledge
```

### Pattern 3: Zero-Shot Agent

```python
# Doubt solving (no retrieval needed)
query = "How do I solve this problem: F=20N, m=5kg, find a?"

classification = tier0.classify_query(query, user_profile)
# → intent=DOUBT

retrieval = await tier1.retrieve(classification, query)
# → Empty (doubt solver doesn't need retrieval)

response = await tier2.execute_agent(
    classification, retrieval, query, user_profile
)

# Result:
# - Agent: DoubtSolverAgent (zero-shot)
# - Confidence: 0.75 (standard for reasoning)
# - Content: Step-by-step solution
```

---

## Agent-Specific Features

### TeacherAgent

**Strategy:** C-RAG (Corrective RAG)

**Prompt Template:**
```
You are an expert tutor explaining {subject} to a {level} student.

Sources:
{retrieved_content}

Student's Question: {query}

Provide a clear explanation using the sources...
```

**Output:**
- Detailed explanation
- Learning objectives
- Related topics
- Next steps

### TrainerAgent

**Strategy:** Few-Shot Learning

**Prompt Template:**
```
Example questions:
{retrieved_questions}

Generate a NEW question about: {focus_area}
Difficulty: {difficulty}

Format as JSON:
{"question": "...", "options": {...}, "correct_answer": "...", "explanation": "..."}
```

**Output:**
- Generated question
- 4 options (A-D)
- Correct answer
- Explanation

### DoubtSolverAgent

**Strategy:** Zero-Shot Reasoning

**Prompt Template:**
```
Student's Problem: {query}

Provide step-by-step solution:
Step 1: ...
Step 2: ...
```

**Output:**
- Step-by-step solution
- Clear reasoning
- Explanations for each step

---

## Performance Targets

| Metric | Target | Typical |
|--------|--------|---------|
| Agent selection | <1ms | 0.2ms |
| Context building | <5ms | 2ms |
| Validation | <1ms | 0.5ms |
| Agent execution | <500ms | 300-600ms |
| Response formatting | <10ms | 5ms |
| **Total Tier-2** | **<600ms** | **300-700ms** |
| **End-to-End (all tiers)** | **<2s** | **0.9-1.5s** |

---

## Error Handling

```python
try:
    response = await tier2.execute_agent(...)
    
    if not response.success:
        # Handle error gracefully
        st.error(response.content['text'])
        logger.error(response.metadata.get('error'))
    
    if response.metadata['confidence_score'] < 0.7:
        # Low confidence warning
        st.warning("Response confidence is low. Please verify.")
    
except Exception as e:
    # Unexpected error
    logger.error(f"Orchestration failed: {e}")
    st.error("An error occurred. Please try again.")
```

---

## Testing

```bash
# Run all tests
pytest tests/routing/test_tier2_orchestrator.py -v

# Specific test
pytest tests/routing/test_tier2_orchestrator.py::test_agent_selection_teach -v

# With coverage
pytest tests/routing/test_tier2_orchestrator.py --cov
```

---

## Troubleshooting

### Issue: Wrong agent selected

**Solution:**
- Check Tier-0 intent classification
- Verify AGENT_MAP configuration
- Review classification confidence

### Issue: Low confidence scores

**Solution:**
- Check retrieval quality (Tier-1)
- Verify sufficient documents retrieved
- Consider adjusting validation thresholds

### Issue: Fallback triggered frequently

**Solution:**
- Check vector store has sufficient content
- Verify Tier-1 filters not too restrictive
- Consider lowering validation thresholds

### Issue: Slow response time

**Solution:**
- Check agent execution time (should be <500ms)
- Verify LLM latency
- Consider caching common responses
- Profile pipeline stages

---

## Integration Checklist

- [ ] Initialize all 3 tiers (Tier-0, Tier-1, Tier-2)
- [ ] Create all 5 agents (Teacher, Trainer, Doubt, Mentor, General)
- [ ] Pass tier1_retriever to orchestrator for fallback
- [ ] Handle response.success flag
- [ ] Display response.content['text']
- [ ] Show metadata in debug/info panel
- [ ] Track performance metrics
- [ ] Log errors appropriately
- [ ] Test all agent types
- [ ] Validate end-to-end latency <2s

---

**Documentation:** [TIER2_ORCHESTRATOR_SUMMARY.md](TIER2_ORCHESTRATOR_SUMMARY.md)  
**Tests:** `tests/routing/test_tier2_orchestrator.py`  
**Status:** ✅ Production Ready
