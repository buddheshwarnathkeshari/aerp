# AERP (Autonomous Engineering Review Platform)

![AERP Dashboard](docs/assets/StartCodeReview.png)

## 🎥 Live Demo

<video src="https://github.com/buddheshwarnathkeshari/aerp/raw/main/docs/assets/Demo.mp4" controls="controls" width="100%"></video>



## 🚀 What it does
AERP is an advanced, AI-powered Autonomous Engineering Review Platform designed to revolutionize the code review process. It acts as a hyper-intelligent, multi-agent code reviewer that automatically analyzes GitHub pull requests against Jira requirements, architectural guidelines, security standards, and performance metrics. 

By orchestrating a swarm of specialized AI agents, AERP performs deep, contextual reviews—catching bugs, security vulnerabilities (OWASP), N+1 queries, and architectural anti-patterns before code is ever merged. It provides engineers with a beautifully designed, real-time dashboard to monitor the review process as the agents deliberate, reach a consensus, and generate actionable findings.

## 🛠️ Technologies Used
AERP is built on a modern, robust full-stack architecture leveraging state-of-the-art AI orchestration and real-time communication.

### Backend & AI Orchestration
* **FastAPI**: High-performance asynchronous Python web framework for the core API.
* **LangChain & LangGraph**: Core AI framework. LangChain provides the abstractions for LLM interactions and tool calling, while LangGraph orchestrates the multi-agent workflows, managing state, cyclic graphs, and decision-making.
* **Retrieval-Augmented Generation (RAG)**:
  * **Vector Database**: PostgreSQL equipped with the `pgvector` extension for storing and querying high-dimensional vectors.
  * **Chunking Strategy**: Employs `RecursiveCharacterTextSplitter` and `MarkdownHeaderTextSplitter` to intelligently chunk architectural guidelines and codebase context without losing semantic meaning.
  * **Similarity Algorithm**: Uses **Cosine Similarity** (`<=>` in pgvector) for highly accurate semantic search retrieval.
* **Human-in-the-Loop (HITL)**: Leverages LangGraph's checkpointer to pause execution on high-risk PRs, requiring explicit human approval before the Consensus Agent finalizes the review.
* **Celery**: Distributed task queue for handling long-running, compute-heavy AI review tasks asynchronously in the background.
* **Redis Stack**: Acts as the Celery message broker, Pub/Sub channel for WebSockets, and state store for LangGraph checkpointers.
* **SQLAlchemy ORM & Alembic**: Robust database modeling, querying, and migration management.
* **PostgreSQL**: Primary relational database for persisting user accounts, integrations, review logs, and vector embeddings.

### Frontend
* **React & Vite**: Lightning-fast frontend development experience.
* **Vanilla CSS (Modern UI)**: Sleek, glassmorphism-inspired UI with modern micro-animations, tailored color palettes, and dark mode aesthetics.
* **Server-Sent Events (SSE)**: Enables real-time streaming of agent execution logs and status updates directly to the UI.

### Infrastructure & Integrations
* **Docker & Docker Compose**: Fully containerized environment for seamless local development and deployment.
* **Authentication**: Robust JWT-based authentication flow with secure password hashing (bcrypt), managing user sessions and protected API routes.
* **OAuth2**: Handles third-party token generation and secure integration management.
* **GitHub API**: Fetches pull requests and diffs dynamically via custom tooling.
* **Jira API**: Cross-references code changes with product requirements and acceptance criteria.

## 🧠 How it works
The magic of AERP lies in its specialized multi-agent architecture. Here is the flow when a new Pull Request is submitted for review:

1. **Context Collection & RAG Pipeline**: The system automatically fetches the PR diff from GitHub and the associated Jira ticket. It then queries the `pgvector` database using Cosine Similarity to retrieve the most relevant architectural guidelines (Google Docs) and injects them into the agents' context windows.
2. **The Orchestrator Agent**: A master routing agent analyzes the scope of the PR (e.g., lines changed, files touched). It intelligently determines which specialized agents are required for the review—for example, skipping the Database Agent if no SQL migrations or ORM queries were modified, saving compute and time.
3. **Parallel Multi-Agent Review**: The selected agents run concurrently to analyze the code from different angles:
    * **Code Review Agent**: Scans for logic errors and bugs.
    * **Security Agent**: Checks for OWASP vulnerabilities and data leaks.
    * **Database Agent**: Analyzes queries for N+1 issues and checks migration safety.
    * **Architecture Agent**: Ensures SOLID principles and design patterns are maintained.
    * **Requirements Agent**: Verifies the code actually fulfills the Jira ticket's acceptance criteria.
    * **Scalability Agent**: Evaluates algorithmic complexity and load performance.
4. **Real-Time Streaming**: As the agents perform their specialized analyses and invoke tools, their statuses are streamed in real-time to the frontend dashboard via Redis Pub/Sub, giving the user a live view of the "AI's thought process".
5. **Human-in-the-Loop (HITL)**: If any agent detects a critical security vulnerability or severe architectural violation, the LangGraph workflow pauses. The platform alerts the engineering manager to review the flagged code and manually approve or reject the continuation of the automated review.
6. **Consensus Agent**: Once all agents (and any required humans) have completed their tasks, the Consensus Agent aggregates all findings. It resolves conflicting advice (e.g., Scalability suggesting caching vs. Security suggesting encryption), calculates a final composite risk score, and presents a structured, actionable report to the engineer.

## 📸 Gallery

### Authentication (Login & Signup)
<br/>
<img src="docs/assets/Login.png" width="400" alt="Login Page">
<img src="docs/assets/Signup.png" width="400" alt="Signup Page">

### User Profile & Settings
<br/>
<img src="docs/assets/ChangePassword.png" width="800" alt="Change Password">

### Connectors (GitHub & Jira)
<br/>
<img src="docs/assets/Connectors.png" width="800" alt="Integrations & Connectors Page">

### Review Workflow & Human-in-the-Loop
<br/>
<img src="docs/assets/StartCodeReview.png" width="800" alt="Start Review Page">
<img src="docs/assets/Reviewing.png" width="800" alt="Review Dashboard">
<img src="docs/assets/HumanInTheLoop.png" width="800" alt="Human In The Loop Approval">

## 🏃‍♂️ Running Locally

1. Make sure you have Docker and Docker Compose installed.
2. Copy `.env.example` to `.env` and fill in your API keys (Gemini, GitHub, Jira).
3. Run `docker compose up -d` to spin up PostgreSQL, Redis Stack, and the Celery worker.
4. Start the backend: `cd backend && uv run uvicorn main:app --reload`
5. Start the frontend: `cd frontend && npm install && npm run dev`
