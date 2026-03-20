# APXMIND - Agents for National Eligibility cum Entrance Test Assistance

> **✅ INTELLIGENCE LAYER COMPLETE**  
> APXMIND's 3-tier intelligent routing system is complete and production-ready!  
> - **Tier-0:** Query Classification (90% accuracy, <5ms) ✅  
> - **Tier-1:** Intelligent Retrieval (88% quality, <1s latency) ✅  
> - **Tier-2:** Agent Orchestration (100% agent selection, <700ms) ✅  
> - **V1 Legacy:** All legacy files removed ✅  
> - **Next:** App Integration (Phase 5 - in progress)  
> - **Documentation:** See [HIERARCHICAL_ROUTING_COMPLETE.md](docs/HIERARCHICAL_ROUTING_COMPLETE.md)

### A Multi-Agent AI Tutor for Democratizing Medical Education in India for the Underserved & Underprivileged

---

##  Vision

APXMIND democratizes NEET coaching, making **high-quality medical education** accessible to every aspiring student in India, especially those in **underprivileged and underserved** communities. Success in NEET often requires expensive coaching that excludes millions of talented students. APXMIND aims to break this barrier with an **offline, AI-powered tutor** designed to run on **low-cost, government-distributed laptops**, no internet connection required.

---

##  Demo

Watch how APXMIND empowers aspiring doctors and levels the educational playing field:

**YouTube Video**: [**APXMIND**](https://youtu.be/C5ptT20AH-4)

**Kaggle Write-up**: [**APXMIND Kaggle Write-up**](https://www.kaggle.com/competitions/google-gemma-3n-hackathon/writeups/APXMIND-agent-for-national-eligibility-cum-entrance)

---

## Key Features

Powered by **Google’s lightweight Gemma-3n model**, APXMIND delivers personalized learning through a **custom multi-agent architecture**. This system operates in **English and various Indian regional languages**, with all content grounded in NCERT textbooks and past NEET papers for maximum accuracy and relevance. This architecture allows a team of specialized agents to collaborate, providing a **holistic and intelligent learning experience** that goes beyond a single chatbot.

<p align="center">
  <img src="Images/APXMIND Tech Report-5_1.png" alt="Agents of APXMIND" width="800"/>
</p>

---

## The Agentic Team

APXMIND operates with a team of specialized agents, each designed for a specific role:

### Mentor Agent  
Guides students with **personalized study plans**, time management, and motivational coaching, drawing insights from **NEET toppers and experts**.

<p align="center">
  <img src="Images/Mentor1.gif" alt="Agents of APXMIND" width="800"/>
</p>

---

### Teacher Agent  
Acts as a **subject-matter expert**, explaining complex concepts in **Physics, Chemistry, and Biology** aligned with the **NCERT** syllabus.

<p align="center">
  <img src="Images/Teacher1.gif" alt="Agents of APXMIND" width="800"/>
</p>

---

### Trainer Agent  
Generates **custom NEET-format quizzes**, based on the style and difficulty of the **last three years’ official papers**.

<p align="center">
  <img src="Images/Quiz1.gif" alt="Agents of APXMIND" width="800"/>
</p>

---

### Doubt Solver Agent  
Provides **quick, precise, and step-by-step solutions** to tough NEET MCQs using **Gemma-3n’**.

<p align="center">
  <img src="Images/Solver1.gif" alt="Agents of APXMIND" width="800"/>
</p>

---

##  Technology Stack

| Component         | Purpose                                                                 |
|------------------|-------------------------------------------------------------------------|
| **Gemma-3n**      | Google’s 2B/4B parameter model for efficient, local, multilingual AI    |
| **nomic-embed-text** | Local embedding model powering offline RAG and content vectorization  |
| **ChromaDB**      | Lightweight, local-first vector DB for similarity search                |
| **Ollama**        | Handles local model deployment (Gemma-3n + embedding models)            |
| **LangGraph**     | Multi-agent orchestration using graph-based framework                  |
| **Streamlit**     | Simple, intuitive UI for learners and educators                         |

---

## Conclusion

APXMIND represents a **major leap toward educational equity**. By providing a **sophisticated, offline, AI-powered tutor** on entry-level hardware, it removes the barriers that keep brilliant students from succeeding due to financial constraints.

With APXMIND, **ambition defines success, not access**.

---

## Disclaimer

This is an **experimental project** developed for the **Google - The Gemma 3n Impact Challenge**.  
The system is currently a **work in progress**. Contributions, suggestions, and feedback are **warmly welcomed**!

---

## Contact

We'd love to hear from you! Reach out with questions, ideas, or just to say hi:

### 👤 Jim Harrington JSN 
- 🧑‍💻 [GitHub](https://github.com/jimdatapro)  
- 💼 [LinkedIn](https://linkedin.com/in/jimdatapro)  
- 📧 jimdatapro@gmail.com

---

### 👤 Jabin Joshua S  
- 🧑‍💻 [GitHub](https://github.com/flarrow27)  
- 💼 [LinkedIn](https://linkedin.com/in/jabinjoshua)  
- 📧 jabinjoshua.s@gmail.com

---

> "Let every dream of becoming a doctor be powered by knowledge, not privilege." 💙

---

## API Smoke Testing

Run reusable API smoke checks against a running backend:

```powershell
python scripts/test_full_api.py --base-url http://127.0.0.1:8000 --profile core --seed-if-empty --ensure-recommendation
```

One-command local run (starts/stops backend automatically):

```powershell
scripts\\run_api_smoke.cmd core
```

For full details, see [API_SMOKE_RUNBOOK.md](docs/API_SMOKE_RUNBOOK.md).
