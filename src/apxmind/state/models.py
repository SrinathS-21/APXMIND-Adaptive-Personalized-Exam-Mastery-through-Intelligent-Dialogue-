from pydantic import BaseModel, Field
from typing import Literal, List, Generator
from typing_extensions import TypedDict
from typing import Annotated
from langchain_core.messages import AnyMessage
# This is the corrected import path for add_messages
from langgraph.graph.message import add_messages

class State(TypedDict):
    """The shared state for the LangGraph workflow."""
    # This part of the code remains the same and will now work correctly
    messages: Annotated[list[AnyMessage], add_messages]
    user_explanation_language: str
    agent_routing: Literal["teacher", "mcq_question_solver", "trainer", "mentor", "general"]
    teacher_vectordb_routing: Literal["biology", "chemistry", "physics", "mentor"]
    response_stream: Generator

class AgentRouteQuery(BaseModel):
    """Pydantic model for the main agent router."""
    datasource_agent_router: Literal["teacher", "mcq_question_solver", "trainer", "mentor", "general"] = Field(..., description="Route to teacher, mcq_question_solver, trainer, mentor, or general.")

class TeacherAgentRouteQuery(BaseModel):
    """Pydantic model for the teacher agent's subject router."""
    datasource_teacher_vectordb_router: Literal["biology", "chemistry", "physics", "mentor"] = Field(..., description="Route to biology, chemistry, or physics or mentor.")

class RelevanceGrader(BaseModel):
    """Pydantic model for grading document relevance."""
    relevance: Literal["yes", "no"] = Field(description="Is the document relevant to the question?")