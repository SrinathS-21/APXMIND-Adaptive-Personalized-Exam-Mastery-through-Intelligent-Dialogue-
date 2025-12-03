import streamlit as st
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

def handle_quiz_ui(selected_language, llm, creative_llm):
    """
    Manages the entire Streamlit UI and logic for an active quiz session.

    Args:
        selected_language (str): The language for explanations.
        llm: The primary LLM instance for evaluation.
        creative_llm: The creative LLM instance for question generation.
    """
    quiz = st.session_state.quiz_state
    st.markdown("---")
    st.subheader(f"Quiz on: {quiz['request']}")
    st.write(f"**Question {quiz['question_number'] + 1} of 5**")
    
    question_placeholder = st.empty()
    feedback_placeholder = st.empty()

    # Generate a new question if one isn't already active
    if not quiz['current_mcq']:
        with st.spinner("Generating next question..."):
            mcq_generation_prompt = PromptTemplate.from_template("""You are a NEET exam question generator. Your goal is to create a series of unique questions.

**Topic:**
{topic}

**Context from existing questions (use for style and topic reference, do not copy):**
{context}

**Previously Generated Questions (IMPORTANT: Do NOT generate these questions or very similar ones again):**
{history}

**Instructions:**
1.  Generate ONE new, unique, and challenging NEET-level Multiple Choice Question (MCQ) on the requested topic.
2.  The question must have four options: (A), (B), (C), (D).
3.  Ensure the question is significantly different from the ones in the history.
4.  Do not reveal the answer or provide an explanation. Just output the question and the four options.
5.  Base the question on the user's request: `{request}`. Use the provided context and topic for guidance, but prioritize your own knowledge to create a high-quality question.
6.  Output only the generated MCQ, nothing else.

**Generated MCQ:**""")
            mcq_generation_chain = mcq_generation_prompt | creative_llm | StrOutputParser()
            history_str = "\n".join(quiz['history']) if quiz['history'] else "None"
            generated_mcq = mcq_generation_chain.invoke({"topic": quiz['neet_query'], "context": quiz['context'], "history": history_str, "request": quiz['request']})
            st.session_state.quiz_state['current_mcq'] = generated_mcq

    # Display the current question and answer options
    with question_placeholder.container():
        st.markdown(st.session_state.quiz_state['current_mcq'])
        user_answer = st.radio("Select your answer:", options=["A", "B", "C", "D"], key=f"q_{quiz['question_number']}", index=None)

    # Handle answer submission
    if st.button("Submit Answer", disabled=(user_answer is None)):
        st.session_state.quiz_state['user_answer'] = user_answer
        with feedback_placeholder.container():
            with st.spinner("Evaluating your answer..."):
                mcq_evaluation_prompt = PromptTemplate.from_template("""You are an expert MCQ evaluator for the NEET exam. Your task is to evaluate the user's answer to the given question.

**Question:**
{question}

**User's Answer:**
{user_answer}

**Instructions:**
1.  State clearly whether the user's answer is 'Correct' or 'Incorrect'.
2.  Provide the correct option (e.g., "The correct answer is (C)").
3.  Give a detailed, step-by-step explanation for why the correct answer is right and the other options are wrong.
4.  First, provide the full explanation in English.
5.  Then, provide the same full explanation in {user_explanation_language}.""")
                mcq_evaluation_chain = mcq_evaluation_prompt | llm | StrOutputParser()
                feedback = mcq_evaluation_chain.invoke({"question": st.session_state.quiz_state['current_mcq'], "user_answer": user_answer, "user_explanation_language": selected_language.lower()})
                st.session_state.quiz_state['feedback'] = feedback
    
    # Display feedback if it exists
    if st.session_state.quiz_state['feedback']:
        feedback_placeholder.info(st.session_state.quiz_state['feedback'])
        is_last_question = st.session_state.quiz_state['question_number'] >= 4
        if is_last_question:
            if st.button("Finish Quiz"):
                final_message = "Quiz complete! I hope that was a helpful practice session. Ask me another question whenever you're ready!"
                st.session_state.messages.append({"role": "assistant", "content": final_message})
                st.session_state.quiz_state = {"active": False}
                st.rerun()
        else:
            if st.button("Next Question"):
                st.session_state.quiz_state['history'].append(st.session_state.quiz_state['current_mcq'])
                st.session_state.quiz_state['question_number'] += 1
                st.session_state.quiz_state['current_mcq'] = ""
                st.session_state.quiz_state['feedback'] = ""
                st.session_state.quiz_state['user_answer'] = None
                st.rerun()

    # Allow user to exit the quiz
    st.markdown("---")
    if st.button("Quit and Exit Quiz"):
        st.session_state.quiz_state = {"active": False}
        st.session_state.messages.append({"role": "assistant", "content": "You have quit the quiz. How can I help you next?"})
        st.rerun()