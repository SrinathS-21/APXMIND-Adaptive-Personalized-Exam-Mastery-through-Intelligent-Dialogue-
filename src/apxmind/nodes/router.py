from ..state.models import State, AgentRouteQuery, TeacherAgentRouteQuery
from ..utils import get_last_human_message
from ..core.resources import llm  # Import the initialized LLM
from langchain_core.prompts import ChatPromptTemplate

def agent_router(state: State):
    """Routes the user query to the appropriate agent."""
    user_query = get_last_human_message(state['messages'])
    agent_structured_llm_router = llm.with_structured_output(AgentRouteQuery)
    system_prompt = """You are an expert AI routing agent. Your sole purpose is to analyze a user's query and classify it into one of four categories based on the user's intent.

1.  'teacher': For conceptual explanations aligned to NEET UG subjects — Biology, Chemistry, and Physics — in open-ended questions (e.g., "what is," "explain," "how does X work") or when requesting specific concepts as a teaching request.
2.  `mcq_question_solver`: For solving a single, specific Multiple-Choice Question (MCQ). The query must contain a full question with options.
3.  `trainer`: For requests for a quiz, train, ask me questions, questions on, mock test, exam, test my knowledge or a series of practice questions.
4.  'mentor': For queries related to NEET preparation, chapters to focus on, how to apply for NEET, top medical schools in India, and any general query related to NEET. What are the top chapters in Physics? How can Apxmind help? Who designed Apxmind? How does Apxmind work? Give me the chapters in Biology. any question related to education or ANEET, help me prepare the top chapters in Biology.
5.  'general': For any queries related to other topics apart from need NEET subjects, what is the capital of india ? who is M.S Dhoni ?
"""
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "Route the following user query: {question}")])
    router_chain = prompt | agent_structured_llm_router
    routing_result = router_chain.invoke({"question": user_query})
    return {"agent_routing": routing_result.datasource_agent_router}

def teacher_vectordb_router(state: State):
    """Routes a teacher query to the correct subject vector database."""
    user_query = get_last_human_message(state['messages'])
    teacher_vectordb_structured_llm_router = llm.with_structured_output(TeacherAgentRouteQuery)
    system_prompt = "You are an expert at routing a user's science question to the correct subject. Choose between 'biology', 'chemistry', or 'physics'."
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{question}")])
    router_chain = prompt | teacher_vectordb_structured_llm_router
    routing_result = router_chain.invoke({"question": user_query})
    return {"teacher_vectordb_routing": routing_result.datasource_teacher_vectordb_router}