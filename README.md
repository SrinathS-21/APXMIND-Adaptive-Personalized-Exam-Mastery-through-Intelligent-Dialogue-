# Apxmind

Powered by Google's lightweight Gemma-3n model, Apxmind delivers personalized learning through a custom multi-agent architecture. The system supports English and multiple Indian regional languages. All content is grounded in NCERT textbooks and past NEET papers to ensure accuracy and relevance.

### A multi-agent AI tutor for democratizing medical education in India

Apxmind aims to make high-quality NEET coaching accessible to every aspiring student in India, especially those from underprivileged and underserved communities. Many students cannot afford expensive coaching; Apxmind provides an offline, AI-powered tutor that can run on low-cost government-distributed laptops without internet access.

## Vision

Democratize NEET coaching by delivering an offline, intelligent, and affordable tutoring system that levels the playing field for students nationwide.

## Key Features

- Personalized learning via a multi-agent architecture.
- Multilingual support (English + Indian regional languages).
- Content grounded in NCERT textbooks and past NEET papers.
- Offline-first design for low-resource hardware.

## The Agentic Team

Each specialized agent has a dedicated role:

- **Mentor Agent** — Provides personalized study plans, time management advice, and motivational coaching informed by NEET toppers and experts.
- **Teacher Agent** — Acts as a subject-matter expert for Physics, Chemistry, and Biology aligned with the NCERT syllabus.
- **Trainer Agent** — Generates custom NEET-format quizzes modeled after recent official papers.
- **Doubt Solver Agent** — Supplies concise, step-by-step solutions to difficult NEET MCQs using Gemma-3n.

## Technology Stack

| Component | Purpose |
|---|---|
| Gemma-3n | Efficient local model for multilingual inference |
| nomic-embed-text | Local embedding model for offline RAG and vectorization |
| ChromaDB | Lightweight, local-first vector database for similarity search |
| Ollama | Local model deployment and runtime management |
| LangGraph | Multi-agent orchestration framework |
| Streamlit | Simple UI for learners and educators |

## Conclusion

Apxmind is a step toward educational equity: an offline, AI-powered tutor designed for entry-level hardware so that ambition — not access — defines success.

> "Let every dream of becoming a doctor be powered by knowledge, not privilege." 💙
