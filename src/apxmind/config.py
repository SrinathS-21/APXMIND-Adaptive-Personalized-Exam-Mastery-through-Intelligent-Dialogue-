# --- Page Configuration Constants ---
PAGE_TITLE = "Apxmind: Agents for National Eligibility Entrance Test Assistance"
TAG_LINE = "In India, many dream of becoming doctors but can't afford costly NEET coaching. Some, like Late Ms. Anitha, tragically gave up after years of struggle. Apxmind uses local AI (Gemma and Ollama) to help underprivileged students prepare offline for NEET UG in their own language, making education accessible and affordable. Apxmind bridges gaps to ensure no dream is limited by money or location."

# --- Language Options ---
ASSISTIVE_LANGUAGE_OPTIONS = ["Tamil", "Hindi", "Bengali", "Telugu", "Marathi"]
DEFAULT_LANGUAGE = "Tamil"

# --- Vector DB Names ---
VECTOR_DB_CONFIGS = {
    'biology': 'chroma_vector_db_biology_nomic',
    'chemistry': 'chroma_vector_db_chemistry_nomic',
    'physics': 'chroma_vector_db_physics_nomic',
    'question_bank': 'chroma_vector_db_questionbank_nomic',
    'mentor': 'chroma_vector_db_mentor_nomic'
}