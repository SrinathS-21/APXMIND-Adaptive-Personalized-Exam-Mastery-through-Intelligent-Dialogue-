"""
Agent Node Implementations
===========================

LangGraph agent nodes for the APXMIND workflow.
Each agent processes a specific type of user query.

Migrated: removed Streamlit dependency (st.spinner, st.session_state).
"""

import logging
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from ..state.models import State, RelevanceGrader
from ..utils import get_last_human_message
from ..llm.llm import get_llm, get_creative_llm
from ..core.tool_runner import AgenticToolRunner

logger = logging.getLogger(__name__)

# NOTE: LLMs are initialized lazily on first call (after app startup sets them up)
# Do NOT call get_llm() at module level — it would fail before init_llm() runs.

from ..vectorstore.storage import ChromaDBManager

# Initialize ChromaDB manager for direct collection access
_chroma_manager = None


def _get_chroma_manager():
    """Lazy initialization of ChromaDB manager."""
    global _chroma_manager
    if _chroma_manager is None:
        _chroma_manager = ChromaDBManager()
    return _chroma_manager


def teacher_agent(state: State):
    """
    Overhauled: Now uses the pure Tool-Calling loop so Llama 3.2 can decide 
    when to search the Vector DB instead of forcing it.
    """
    llm = get_llm()
    query = get_last_human_message(state["messages"])
    lang = state["user_explanation_language"]

    # We extract the pure Llama object from LangChain's ChatLlamaCpp client wrapper
    # This allows us to use true function calling without Langchain formatting bugs
    native_llama_client = llm.client

    system_prompt = (
        f"You are a NEET Medical tutor. You MUST use your search tools if the user asks a factual "
        f"science question about Biology, Chemistry, or Physics. DO NOT guess the curriculum facts. "
        f"After retrieving the facts, explain the answer in simple English, and then provide a "
        f"translation in {lang}. Do NOT mention 'NEET aspirant' in your output."
    )

    runner = AgenticToolRunner(native_llama_client)

    return {
        "response_stream": runner.chat_with_tools_stream(
            user_query=query, 
            system_prompt=system_prompt
        )
    }


def mcq_question_solver_agent(state: State):
    llm = get_llm()
    user_query = get_last_human_message(state["messages"])
    lang = state["user_explanation_language"]
    question_solver_system_template = (
        "You are a specialist in biology, chemistry, and physics, responsible for "
        "answering NEET entrance exam questions (MCQ format questions) and providing "
        "clear explanations in English and {user_explanation_language} to help NEET "
        "medical aspirants understand how the solution was reached. DO NOT MENTION "
        "NEET ASPIRANT IN OUTPUT Do not add any extra text or repeat the English "
        "answer after the translation and If you don't know how to translate then "
        "use english word or skip it."
    )
    prompt = ChatPromptTemplate.from_messages(
        [("system", question_solver_system_template), ("human", "{question}")]
    )
    question_solver_chain = prompt | llm | StrOutputParser()
    return {
        "response_stream": question_solver_chain.stream(
            {"question": user_query, "user_explanation_language": lang}
        )
    }


def trainer_agent(state: State):
    llm = get_llm()
    original_user_query = get_last_human_message(state["messages"])

    logger.info("Preparing quiz materials...")

    # Get question_bank collection directly from ChromaDB
    chroma_manager = _get_chroma_manager()
    question_bank_store = chroma_manager.get_collection("question_bank")

    if not question_bank_store:

        def error_stream():
            yield "Cannot start quiz: The question bank is not loaded."

        return {"response_stream": error_stream()}

    reformulate_prompt = PromptTemplate.from_template(
        "Reformulate the following user request into a suitable query for searching "
        "a NEET exam question database. Focus on extracting the core subject and topic.\n\n"
        "User Request: '{request}'\n\nReformulated Query:"
    )
    reformulate_chain = reformulate_prompt | llm | StrOutputParser()
    neet_query = reformulate_chain.invoke({"request": original_user_query})

    def retrieve_and_grade(k_val):
        retriever = question_bank_store.as_retriever(search_kwargs={"k": k_val})
        retrieved_docs = retriever.invoke(neet_query)
        grading_prompt = ChatPromptTemplate.from_template(
            "Is the retrieved document relevant to the user's original request for a quiz?\n\n"
            "User Request: {question}\nRetrieved Document:\n<document>{document}</document>"
        )
        relevance_grader_chain = grading_prompt | llm.with_structured_output(RelevanceGrader)
        return [
            doc
            for doc in retrieved_docs
            if relevance_grader_chain.invoke(
                {"question": original_user_query, "document": doc.page_content}
            ).relevance
            == "yes"
        ]

    relevant_docs = retrieve_and_grade(k_val=5)
    if len(relevant_docs) < 3:
        relevant_docs = retrieve_and_grade(k_val=10)

    context_str = (
        "\n\n".join([doc.page_content for doc in relevant_docs])
        if relevant_docs
        else "No context available. Generate a general question based on the topic."
    )

    # Store quiz context in state (no more st.session_state)
    quiz_state = {
        "active": True,
        "question_number": 0,
        "history": [],
        "context": context_str,
        "request": original_user_query,
        "neet_query": neet_query,
        "current_mcq": "",
        "feedback": "",
        "user_answer": None,
    }

    def start_quiz_stream():
        yield "I've prepared a 5-question quiz for you. Let's begin!"

    return {"response_stream": start_quiz_stream(), "quiz_state": quiz_state}


def mentor_agent(state: State):
    llm = get_llm()
    query = get_last_human_message(state["messages"])
    lang = state["user_explanation_language"]

    # Get mentor collection directly from ChromaDB
    chroma_manager = _get_chroma_manager()
    vectorstore = chroma_manager.get_collection("mentor")

    fallback_template = (
        "You are a helpful NEET mentor. Answer the user's question from your general "
        "knowledge as the internal knowledge base did not contain relevant information. "
        "Explain in simple English, then explain in {user_explanation_language}.\n\n"
        "Question:\n{question} Do not add any extra text or repeat the English answer "
        "after the translation. If you don't know how to translate then use english word or skip it."
    )
    fallback_chain = PromptTemplate.from_template(fallback_template) | llm | StrOutputParser()

    if not vectorstore:
        return {
            "response_stream": fallback_chain.stream(
                {"question": query, "user_explanation_language": lang}
            )
        }

    grading_prompt = ChatPromptTemplate.from_template(
        "Is the retrieved document relevant to the user's question about NEET preparation, "
        "strategy, or medical education?\n\nUser Question: {question}\n"
        "Retrieved Document:\n<document>{document}</document>"
    )
    relevance_grader_chain = grading_prompt | llm.with_structured_output(RelevanceGrader)

    retriever_k3 = vectorstore.as_retriever(search_kwargs={"k": 3})
    filtered_docs = [
        doc
        for doc in retriever_k3.invoke(query)
        if relevance_grader_chain.invoke(
            {"question": query, "document": doc.page_content}
        ).relevance
        == "yes"
    ]

    if len(filtered_docs) < 2:
        retriever_k10 = vectorstore.as_retriever(search_kwargs={"k": 10})
        filtered_docs = [
            doc
            for doc in retriever_k10.invoke(query)
            if relevance_grader_chain.invoke(
                {"question": query, "document": doc.page_content}
            ).relevance
            == "yes"
        ]

    if len(filtered_docs) >= 2:
        context_str = "\n\n".join(doc.page_content for doc in filtered_docs)
        rag_template = (
            "You are a helpful NEET mentor. Answer the user's question based ONLY on "
            "the provided context. Explain in simple English, then explain in "
            "{user_explanation_language}.\n\nContext:\n{context}\n\nQuestion:\n{question} "
            "Do not add any extra text or repeat the English answer after the translation. "
            "If you don't know how to translate then use english word or skip it."
        )
        rag_chain = PromptTemplate.from_template(rag_template) | llm | StrOutputParser()
        return {
            "response_stream": rag_chain.stream(
                {"context": context_str, "question": query, "user_explanation_language": lang}
            )
        }
    else:
        return {
            "response_stream": fallback_chain.stream(
                {"question": query, "user_explanation_language": lang}
            )
        }


def general_query_agent(state: State):
    llm = get_llm()
    query = get_last_human_message(state["messages"])
    lang = state.get("user_explanation_language", "English")
    system_template = (
        "You are a helpful general-purpose AI assistant. "
        "First, answer the user's question clearly and concisely in English. "
        "Then, on a new line, provide a direct translation of your English answer into "
        "{user_explanation_language}. "
        "Do not add any extra text or repeat the English answer after the translation."
        "If you don't know how to translate then use english word or skip it."
    )
    prompt = ChatPromptTemplate.from_messages(
        [("system", system_template), ("human", "{question}")]
    )
    general_chain = prompt | llm | StrOutputParser()
    return {
        "response_stream": general_chain.stream(
            {"question": query, "user_explanation_language": lang}
        )
    }
