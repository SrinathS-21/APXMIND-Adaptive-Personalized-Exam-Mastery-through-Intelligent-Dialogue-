import streamlit as st
from langgraph.graph import END, StateGraph, START
from ..state.models import State
from ..nodes.router import agent_router, teacher_vectordb_router
from ..nodes.agents import (
    teacher_agent, 
    mcq_question_solver_agent, 
    trainer_agent, 
    mentor_agent, 
    general_query_agent
)

@st.cache_resource
def get_graph():
    """Builds and compiles the LangGraph agent workflow."""
    builder = StateGraph(State)

    # Add all nodes to the graph
    builder.add_node("agent_router", agent_router)
    builder.add_node("teacher_vectordb_router", teacher_vectordb_router)
    builder.add_node('teacher_agent', teacher_agent)
    builder.add_node('mcq_question_solver_agent', mcq_question_solver_agent)
    builder.add_node('trainer_agent', trainer_agent)
    builder.add_node('mentor_agent', mentor_agent)
    builder.add_node('general_query_agent', general_query_agent)
    
    # Define the workflow edges
    builder.add_edge(START, "agent_router")
    
    builder.add_conditional_edges(
        "agent_router", 
        lambda s: s["agent_routing"], 
        {
           "teacher": "teacher_vectordb_router", 
           "mcq_question_solver": "mcq_question_solver_agent",
           "trainer": "trainer_agent", 
           "mentor": "mentor_agent", 
           "general": "general_query_agent"
        }
    )
    
    builder.add_edge("teacher_vectordb_router", "teacher_agent")

    # All worker agents lead to the end
    builder.add_edge("teacher_agent", END)
    builder.add_edge("mcq_question_solver_agent", END)
    builder.add_edge("trainer_agent", END)
    builder.add_edge("mentor_agent", END)
    builder.add_edge("general_query_agent", END)
    
    return builder.compile()