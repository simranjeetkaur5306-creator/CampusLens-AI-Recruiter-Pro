# CampusLens AI

## Intelligent AI-Powered Recruitment and Career Recommendation System

CampusLens AI is an AI-powered recruitment and career recommendation platform designed primarily for campus and early-career recruitment.

The system aims to improve traditional recruitment workflows by moving beyond keyword-based resume screening and using NLP, text embeddings, semantic similarity search, candidate ranking, skill-gap analysis, job recommendation, and LLM-assisted interview support.

> **Academic Project:** Final Year B.Tech Project  
> **Specialization:** Artificial Intelligence & Machine Learning  
> **University:** Kurukshetra University  
> **Academic Year:** 2026–2027

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Problem Statement](#-problem-statement)
- [Objectives](#-objectives)
- [Key Features](#-key-features)
- [User Roles](#-user-roles)
- [System Workflow](#-system-workflow)
- [AI/ML Pipeline](#-aiml-pipeline)
- [System Architecture](#-system-architecture)
- [Technology Stack](#-technology-stack)
- [Database Design](#-database-design)
- [Project Structure](#-project-structure)
- [Functional Modules](#-functional-modules)
- [Installation & Setup](#-installation--setup)
- [Environment Variables](#-environment-variables)
- [Running the Project](#-running-the-project)
- [API Overview](#-api-overview)
- [Matching Methodology](#-matching-methodology)
- [Skill-Gap Analysis](#-skill-gap-analysis)
- [Job Recommendation](#-job-recommendation)
- [AI Interview Assistant](#-ai-interview-assistant)
- [Recruitment Analytics](#-recruitment-analytics)
- [Testing & Evaluation](#-testing--evaluation)
- [Security & Privacy](#-security--privacy)
- [Limitations](#-limitations)
- [Future Scope](#-future-scope)
- [Development Roadmap](#-development-roadmap)
- [Project Outcomes](#-project-outcomes)
- [Disclaimer](#-disclaimer)

---

# 🚀 Overview

Traditional recruitment systems often depend heavily on manual resume screening or keyword-based Applicant Tracking Systems (ATS).

Keyword-based matching may fail when a candidate has relevant experience but uses terminology that differs from the wording of a Job Description (JD).

CampusLens AI proposes a semantic approach in which resumes and job descriptions are processed using NLP techniques and represented as dense vector embeddings.

These embeddings are stored and searched using PostgreSQL with the `pgvector` extension.

The system then uses semantic similarity to identify potentially relevant candidates.

The platform also provides:

- Candidate ranking
- Skill-gap analysis
- Job recommendations
- Recruiter analytics
- Candidate dashboards
- AI-assisted interview-question generation
- Basic recruitment communication support

---

# 🎯 Problem Statement

Recruiters handling a large number of applications face several challenges:

- Manual resume screening is time-consuming.
- Manual screening becomes difficult to scale.
- Keyword-based ATS filtering can miss relevant candidates using different terminology.
- Candidate ranking can vary between recruiters.
- Candidates often receive little structured feedback about skill gaps.
- Recruiters may lack consolidated analytics about applicant pools.
- Interview preparation and question generation can be manual and unstructured.

CampusLens AI aims to address these challenges through a semantic, AI-assisted recruitment workflow.

---

# 🎯 Objectives

The major objectives of CampusLens AI are:

1. Design and implement a web-based recruitment platform with separate candidate and recruiter roles.
2. Implement JWT-based authentication and role-based access control.
3. Develop a resume parsing module for PDF and DOCX resumes.
4. Extract structured information such as skills, education, experience, and contact details.
5. Provide job-description creation and management functionality.
6. Generate vector embeddings for resumes and job descriptions.
7. Implement semantic similarity search using PostgreSQL and pgvector.
8. Rank candidates according to their relevance to a job description.
9. Perform skill-gap analysis between candidate skills and job requirements.
10. Generate role-relevant interview questions using an LLM.
11. Provide candidate and recruiter dashboards.
12. Provide basic recruitment analytics.
13. Provide relevant job recommendations to candidates.
14. Evaluate the system using appropriate qualitative and quantitative metrics.

---

# ✨ Key Features

## Candidate Features

- Candidate registration and login
- JWT authentication
- Resume upload
- PDF/DOCX resume support
- Resume information extraction
- Skill extraction
- Education extraction
- Experience extraction
- Job application tracking
- Match scores
- Skill-gap analysis
- Job recommendations
- AI-assisted interview preparation

## Recruiter Features

- Recruiter registration and login
- Recruiter profile
- Job Description creation
- Job Description editing
- Job publishing
- Applicant management
- Semantic candidate matching
- Candidate ranking
- Match-score visualization
- Skill-gap insights
- AI-generated interview questions
- Recruitment analytics
- Application-status management
- Basic recruitment communication

---

# 👥 User Roles

CampusLens AI provides two primary user roles.

## Candidate

A candidate can:

- Create an account
- Login securely
- Upload a resume
- View extracted resume information
- View skills and experience
- Apply for available jobs
- View application status
- View match information
- Identify skill gaps
- Receive job recommendations
- Generate interview-preparation questions

## Recruiter

A recruiter can:

- Create an account
- Login securely
- Manage recruiter profile
- Create Job Descriptions
- Edit and publish jobs
- View applicants
- View candidate rankings
- View match scores
- Analyze candidate skill gaps
- Generate interview questions
- Manage application statuses
- View recruitment analytics

---

# 🔄 System Workflow

```text
                 Candidate / Recruiter
                         |
                         v
                  React Frontend
                         |
                         v
                 Django REST API
                         |
          +--------------+--------------+
          |                             |
          v                             v
    Authentication                AI/NLP Layer
          |                             |
          |                    +--------+--------+
          |                    |                 |
          |                    v                 v
          |              Resume Parsing      JD Processing
          |                    |                 |
          |                    +--------+--------+
          |                             |
          |                             v
          |                    Information Extraction
          |                             |
          |                             v
          |                    Embedding Generation
          |                             |
          |                             v
          |                    PostgreSQL + pgvector
          |                             |
          |                             v
          |                    Semantic Similarity
          |                             |
          |                    +--------+--------+
          |                    |        |        |
          |                    v        v        v
          |                 Matching Ranking Skill Gap
          |                                      |
          |                                      v
          |                              Recommendations
          |                                      |
          |                                      v
          |                              LLM Assistance
          |                                      |
          +----------------------+---------------+
                                 |
                                 v
                          Dashboard Results
```

---

# 🧠 AI/ML Pipeline

The core AI/ML workflow is:

```text
Resume / Job Description
          |
          v
    Text Extraction
          |
          v
   Text Preprocessing
          |
          v
Information & Skill Extraction
          |
          v
   Embedding Generation
          |
          v
   PostgreSQL + pgvector
          |
          v
   Cosine Similarity
          |
          v
 Candidate Matching
          |
          v
 Candidate Ranking
          |
          v
  Skill-Gap Analysis
          |
          v
 Job Recommendation
          |
          v
LLM-Assisted Interview Questions
```

---

# 🏗️ System Architecture

CampusLens AI follows a layered client-server architecture.

```text
┌───────────────────────────────────────┐
│              USERS                    │
│      Candidate / Recruiter            │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│          REACT FRONTEND               │
│ Forms • Dashboards • Applications     │
└──────────────────┬────────────────────┘
                   │ REST API
                   ▼
┌───────────────────────────────────────┐
│       DJANGO REST FRAMEWORK           │
│ Authentication • Validation           │
│ Business Logic • API Routing          │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│          AI / NLP LAYER               │
│ Resume Parsing • Information          │
│ Extraction • LLM Processing           │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│       EMBEDDING GENERATION            │
│ Resume Embeddings + JD Embeddings     │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│       POSTGRESQL + PGVECTOR           │
│ Relational Data + Vector Search       │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│       MATCHING & RANKING              │
│ Similarity • Ranking • Skill Gaps     │
└──────────────────┬────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────┐
│        DASHBOARDS & ANALYTICS         │
└───────────────────────────────────────┘
```

---

# 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| React.js | Frontend user interface |
| JavaScript | Frontend application logic |
| Django | Backend framework |
| Django REST Framework | REST API layer |
| Python | Backend, NLP and AI processing |
| PostgreSQL | Primary relational database |
| pgvector | Vector storage and similarity search |
| JWT | Authentication and authorization |
| OpenAI API | LLM-assisted tasks and embedding-related processing |
| REST APIs | Frontend-backend communication |
| Git | Version control |
| GitHub | Source-code repository |
| Postman | API testing |
| PDF/DOCX libraries | Resume text extraction |

---

# 🗄️ Database Design

The main database entities are:

```text
Users
Candidates
Recruiters
Resumes
Skills
JobDescriptions
Applications
MatchScores
Interviews
Recommendations
```

## Entity Relationships

```text
                  ┌──────────────┐
                  │    Users     │
                  └──────┬───────┘
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
       ┌─────────────┐       ┌─────────────┐
       │ Candidates  │       │ Recruiters  │
       └──────┬──────┘       └──────┬──────┘
              │                     │
              ▼                     ▼
        ┌───────────┐         ┌───────────────┐
        │  Resumes  │         │ JobDescriptions│
        └─────┬─────┘         └───────┬───────┘
              │                       │
              │                       │
              └──────────┬────────────┘
                         ▼
                  ┌─────────────┐
                  │ MatchScores  │
                  └─────────────┘

Candidates ─────── Applications ─────── JobDescriptions
                         │
                         ▼
                    Interviews

Candidates ───── Recommendations ───── JobDescriptions
```

---

# 📁 Project Structure

```text
CampusLens-AI/
│
├── backend/
│   │
│   ├── config/
│   │
│   ├── users/
│   │
│   ├── candidates/
│   │
│   ├── recruiters/
│   │
│   ├── resumes/
│   │
│   ├── jobs/
│   │
│   ├── matching/
│   │
│   ├── recommendations/
│   │
│   ├── interviews/
│   │
│   ├── analytics/
│   │
│   ├── ai/
│   │
│   ├── prompts/
│   │
│   ├── manage.py
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   │
│   ├── public/
│   │
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── context/
│   │   ├── hooks/
│   │   └── utils/
│   │
│   ├── package.json
│   └── vite.config.js
│
├── docs/
│   ├── architecture/
│   ├── database/
│   ├── diagrams/
│   └── testing/
│
├── .gitignore
├── .env.example
├── README.md
└── docker-compose.yml
```

---

# 🧩 Functional Modules

## 1. Authentication & Role Management

Provides:

- Registration
- Login
- JWT authentication
- Role-based authorization
- Candidate permissions
- Recruiter permissions

---

## 2. Resume Upload & Parsing

Candidates can upload:

- PDF
- DOCX

Processing:

```text
Resume
 ↓
File Validation
 ↓
Text Extraction
 ↓
Text Cleaning
 ↓
Structured Processing
```

The system should handle unsupported or corrupted files gracefully.

---

## 3. Resume Information Extraction

The system extracts relevant information such as:

- Name
- Email
- Phone
- Skills
- Education
- Experience
- Projects
- Certifications where available

The extracted information is stored as structured data.

---

## 4. Job Description Management

Recruiters can:

- Create jobs
- Edit jobs
- Publish jobs
- Manage job requirements
- Specify required skills
- Specify experience level
- Specify education requirements
- Add role details

---

## 5. Semantic Resume-JD Matching

Instead of relying only on exact keywords, the system represents resume and JD text as vector embeddings.

```text
Resume Text
     ↓
Embedding
     ↓
Vector

JD Text
     ↓
Embedding
     ↓
Vector

Vector + Vector
     ↓
Cosine Similarity
     ↓
Semantic Match
```

---

## 6. Candidate Ranking

Candidates are ranked for a selected JD according to their computed semantic relevance.

Example:

```text
Candidate A → Similarity Score
Candidate B → Similarity Score
Candidate C → Similarity Score
```

The system assists recruiters in prioritizing candidate review.

---

## 7. Skill-Gap Analysis

The system compares:

```text
Candidate Skills
        VS
Required Job Skills
```

It identifies:

- Matched skills
- Missing skills
- Partially relevant skills

This information can provide candidates with structured feedback.

---

## 8. Job Recommendation

Candidate profile/resume information is compared with available job descriptions.

```text
Candidate Profile
       ↓
Embedding
       ↓
Compare with Open Jobs
       ↓
Semantic Similarity
       ↓
Relevant Job Recommendations
```

---

## 9. AI Interview Question Generation

The LLM can generate interview questions based on:

- Job Description
- Candidate profile
- Candidate skills
- Relevant skill gaps

Potential question categories:

- Technical
- Role-specific
- Behavioral
- Skill-gap related

---

## 10. Candidate Dashboard

The candidate dashboard can display:

- Profile
- Resume
- Skills
- Applications
- Application status
- Match scores
- Skill gaps
- Recommended jobs
- Interview preparation

---

## 11. Recruiter Dashboard

The recruiter dashboard can display:

- Jobs
- Applicants
- Candidate ranking
- Match scores
- Skill gaps
- Application status
- Analytics
- Interview-question generation

---

## 12. Recruitment Analytics

The system provides basic analytics such as:

- Number of applications
- Application status
- Average match scores
- Common skills
- Common skill gaps
- Job-wise applicant counts

---

## 13. Email / Interview Automation

The system supports basic recruitment communication such as:

```text
Application Received
        ↓
Status Update
        ↓
Shortlisted
        ↓
Interview Communication
```

The exact implementation can depend on the available communication service and project deployment environment.

---

# 🔍 Matching Methodology

The matching system follows these steps:

### Step 1 — Resume Processing

The resume is converted into usable text.

### Step 2 — JD Processing

The job description is cleaned and structured.

### Step 3 — Embedding Generation

Both texts are converted into dense vector representations.

### Step 4 — Vector Storage

Embeddings are stored using PostgreSQL with pgvector.

### Step 5 — Similarity Calculation

Cosine similarity is used to compare the vectors.

### Step 6 — Candidate Retrieval

Semantically relevant candidates are identified.

### Step 7 — Ranking

Candidates are ordered according to their computed similarity/relevance score.

---

# 📐 Cosine Similarity

Cosine similarity measures the similarity between two vectors.

Conceptually:

```text
              A · B
Cosine =  -------------
           ||A|| ||B||
```

Where:

- `A` = Resume embedding
- `B` = Job Description embedding

A higher similarity indicates that the two vector representations are more semantically similar.

The actual scoring behaviour will be evaluated during testing.

---

# 🧠 Skill-Gap Analysis

Skill-gap analysis compares extracted candidate skills against the required skills of a job.

Example:

```text
Required Skills:
Python
Django
PostgreSQL
React
AWS

Candidate Skills:
Python
Django
PostgreSQL
React
```

Possible output:

```text
Matched:
✓ Python
✓ Django
✓ PostgreSQL
✓ React

Missing:
✗ AWS
```

This provides candidates with more structured feedback about areas they may need to develop.

---

# 💼 Job Recommendation

Job recommendation uses semantic similarity between:

```text
Candidate Resume/Profile
              +
Available Job Descriptions
              ↓
       Embedding Comparison
              ↓
     Similarity Calculation
              ↓
      Relevant Job Ranking
              ↓
       Job Recommendations
```

Only available/open job descriptions should be considered for active recommendations.

---

# 🤖 AI Interview Assistant

The AI interview module uses an LLM to generate questions based on the role and candidate context.

Example input:

```text
Job:
AI/ML Engineer

Candidate Skills:
Python
Machine Learning
Django
PostgreSQL
NLP
```

The system can generate questions related to:

- Machine Learning
- Python
- NLP
- Backend development
- Database concepts
- Role-specific requirements
- Candidate skill gaps

---

# 📊 Recruitment Analytics

Analytics may include:

```text
Total Applications
        ↓
Application Status
        ↓
Shortlisted
Interview
Selected / Rejected
```

Additional analytics:

- Average match score
- Common candidate skills
- Common skill gaps
- Applicants per job
- Application-status distribution

Analytics are calculated from actual application and matching data rather than fabricated values.

---

# 🔐 Security & Privacy

CampusLens AI handles resume information that may contain personal data.

The system therefore considers:

- JWT authentication
- Role-based access control
- Secure password hashing
- File validation
- File-size restrictions
- Protected APIs
- Environment variables
- Secure API-key handling
- Appropriate access control
- Limited transmission of resume information to third-party AI APIs

### Important

Never commit API keys or passwords to GitHub.

The following should remain private:

```text
.env
API keys
Database passwords
Secret keys
Personal credentials
```

---

# ⚙️ Installation & Setup

## Prerequisites

Install:

- Python 3.x
- Node.js
- npm
- PostgreSQL
- pgvector
- Git
- VS Code
- Postman

An OpenAI API key is required for the relevant LLM/embedding functionality.

---

# 🐍 Backend Setup

Open terminal:

```bash
cd backend
```

Create virtual environment:

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run migrations:

```bash
python manage.py migrate
```

Create superuser:

```bash
python manage.py createsuperuser
```

Start backend:

```bash
python manage.py runserver
```

Backend will normally run at:

```text
http://127.0.0.1:8000/
```

---

# ⚛️ Frontend Setup

Open a second terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start frontend:

```bash
npm run dev
```

Frontend will normally run at:

```text
http://localhost:5173/
```

---

# 🐘 PostgreSQL Setup

Create a PostgreSQL database:

```text
Database:
campuslens
```

Example configuration:

```text
Host: localhost
Port: 5432
Database: campuslens
User: postgres
```

Enable pgvector:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Verify:

```sql
SELECT * FROM pg_extension
WHERE extname = 'vector';
```

---

# 🔑 Environment Variables

Create:

```text
backend/.env
```

Example:

```env
SECRET_KEY=your_django_secret_key
DEBUG=True

DB_NAME=campuslens
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432

OPENAI_API_KEY=your_openai_api_key
```

Create:

```text
.env.example
```

without real credentials:

```env
SECRET_KEY=
DEBUG=True

DB_NAME=campuslens
DB_USER=postgres
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432

OPENAI_API_KEY=
```

---

# ▶️ Running the Complete Project

Use two terminals.

## Terminal 1 — Backend

```bash
cd backend
venv\Scripts\activate
python manage.py runserver
```

## Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

Then open:

```text
Frontend:
http://localhost:5173/

Backend:
http://127.0.0.1:8000/
```

---

# 🔌 API Overview

The application will expose REST APIs for major system modules.

## Authentication

```text
POST /api/auth/register/
POST /api/auth/login/
POST /api/auth/refresh/
```

## Candidate

```text
GET  /api/candidate/profile/
POST /api/candidate/resume/
GET  /api/candidate/applications/
GET  /api/candidate/recommendations/
```

## Jobs

```text
POST   /api/jobs/
GET    /api/jobs/
GET    /api/jobs/{id}/
PUT    /api/jobs/{id}/
DELETE /api/jobs/{id}/
```

## Matching

```text
GET /api/jobs/{id}/matches/
GET /api/candidates/{id}/match/{job_id}/
```

## Skill Gap

```text
GET /api/candidates/{id}/skill-gap/{job_id}/
```

## Interviews

```text
POST /api/interviews/generate-questions/
GET  /api/interviews/{id}/
```

## Analytics

```text
GET /api/analytics/recruiter/
GET /api/analytics/job/{id}/
```

> Endpoint names may be adjusted during implementation while maintaining REST principles.

---

# 🧪 Testing & Evaluation

The project will be evaluated after implementation.

## 1. Resume Parsing Accuracy

Compare extracted:

- Skills
- Education
- Experience
- Contact information

against manually verified ground truth.

---

## 2. Matching Precision / Recall

Where feasible, use a manually labelled sample of resume-JD pairs to evaluate whether relevant resumes are retrieved.

---

## 3. Ranking Quality

Check whether candidates ranked higher are generally more relevant to the selected job description than candidates ranked lower.

---

## 4. Semantic Similarity Behaviour

Test examples such as:

```text
Relevant Resume ↔ Relevant JD
```

versus:

```text
Unrelated Resume ↔ JD
```

and verify that similarity behaves sensibly.

---

## 5. Response Time

Measure response time for important operations such as:

- Resume processing
- Matching
- Dashboard loading
- API requests

---

## 6. API Reliability

Test:

- Valid requests
- Invalid requests
- Missing fields
- Unauthorized access
- Invalid files
- API failures

---

## 7. Usability

Collect basic feedback from peers or guide review regarding:

- Interface clarity
- Ease of navigation
- Dashboard usability
- Overall workflow

---

# 📈 Evaluation Results

No numerical performance results are claimed at the proposal stage.

Final values such as:

- Parsing accuracy
- Precision
- Recall
- Ranking performance
- Response time

will be added after actual implementation and testing.

---

# ⚠️ Limitations

## Resume Format Variability

Unconventional layouts, scanned resumes, or heavily formatted documents may reduce parsing quality.

## LLM Dependency

LLM-assisted functionality depends on an external API and may involve:

- Availability limitations
- Rate limits
- Usage costs

## Recruitment AI Bias

Embedding and language models may reflect biases present in their underlying training data or language patterns.

## Data Privacy

Resumes contain personal information and require careful storage and processing.

## API Costs

External AI APIs may introduce operational costs as usage increases.

## Model Limitations

General-purpose pretrained models are not specifically fine-tuned for recruitment.

## Human Oversight

CampusLens AI is a decision-support system and should not be used as the sole basis for hiring decisions.

---

# 🔮 Future Scope

Potential future improvements include:

### Advanced RAG

Use Retrieval-Augmented Generation to ground AI responses in verified candidate and job data.

### Domain-Specific Models

Fine-tune embedding or language models using recruitment-specific data.

### Multilingual Resume Processing

Support resumes written in languages beyond English.

### Explainable AI

Provide more transparent explanations of match scores and rankings.

### Bias Detection

Introduce formal bias detection and fairness auditing.

### Voice-Based Interviews

Add voice-based preliminary interview functionality.

### OCR

Support scanned/image-based resumes.

### Cloud Deployment

Deploy the platform to cloud infrastructure for broader accessibility.

### MLOps

Introduce model monitoring, versioning and retraining pipelines.

### Predictive Hiring Analytics

Use historical data to investigate:

- Time-to-hire
- Applicant-pool trends
- Recruitment forecasting

---

# 🗺️ Development Roadmap

## Phase 1 — Project Foundation

- Project structure
- Git/GitHub
- Django setup
- React setup
- PostgreSQL setup
- pgvector setup
- Environment configuration

## Phase 2 — Authentication

- User model
- Candidate role
- Recruiter role
- JWT authentication
- Role-based access control

## Phase 3 — Resume Module

- Resume upload
- PDF parsing
- DOCX parsing
- Text preprocessing
- Information extraction
- Skill extraction

## Phase 4 — Job Module

- Create JD
- Edit JD
- Publish JD
- Required skills
- Experience
- Education
- Job management

## Phase 5 — Semantic Matching

- Embedding generation
- Vector storage
- pgvector integration
- Cosine similarity
- Candidate matching
- Candidate ranking

## Phase 6 — Recommendations

- Skill-gap analysis
- Job recommendations

## Phase 7 — AI Interview Assistant

- Interview question generation
- Candidate-specific questions
- Role-specific questions

## Phase 8 — Dashboards

- Candidate dashboard
- Recruiter dashboard
- Match-score display
- Skill-gap display
- Application status

## Phase 9 — Analytics & Automation

- Recruitment analytics
- Application events
- Basic email/status communication
- Interview scheduling communication

## Phase 10 — Testing & Evaluation

- Unit testing
- Integration testing
- API testing
- Parsing evaluation
- Matching evaluation
- Ranking evaluation
- Performance testing
- Usability feedback

## Phase 11 — Documentation

- README
- Architecture diagram
- ER diagram
- DFD
- API documentation
- Testing documentation
- Final project report

---

# 📚 Core AI/ML Concepts Demonstrated

CampusLens AI demonstrates practical use of:

- Natural Language Processing
- Text preprocessing
- Information extraction
- Named-entity/information extraction
- Text embeddings
- Vector databases
- Semantic similarity
- Cosine similarity
- Vector search
- Recommendation systems
- Score-based ranking
- Skill-gap analysis
- Large Language Models
- Full-stack AI application development

---

# 🎓 Academic Relevance

CampusLens AI combines:

```text
Artificial Intelligence
        +
Machine Learning
        +
Natural Language Processing
        +
Vector Search
        +
Large Language Models
        +
Database Systems
        +
Full-Stack Development
```

This makes the project suitable for demonstrating practical application of AI & ML concepts in a real-world recruitment workflow.

---

# 📷 Screenshots

Screenshots will be added after the user interface is implemented.

Planned screenshots:

- Login
- Candidate registration
- Recruiter registration
- Candidate dashboard
- Recruiter dashboard
- Resume upload
- Resume analysis
- Job creation
- Candidate ranking
- Skill-gap analysis
- Job recommendations
- AI interview questions
- Recruitment analytics

---

# 📊 Project Evaluation Status

| Component | Status |
|---|---|
| Project Architecture | Planned |
| React Frontend | In Development |
| Django Backend | Planned |
| PostgreSQL | Planned |
| pgvector | Planned |
| JWT Authentication | Planned |
| Resume Parsing | Planned |
| Information Extraction | Planned |
| Semantic Matching | Planned |
| Candidate Ranking | Planned |
| Skill-Gap Analysis | Planned |
| Job Recommendation | Planned |
| AI Interview Assistant | Planned |
| Candidate Dashboard | Planned |
| Recruiter Dashboard | Planned |
| Analytics | Planned |
| Testing | Planned |
| Deployment | Future Stage |

> Status will be updated as each component is actually implemented and tested.

---

# 📖 References

The project is based on concepts and technologies including:

1. Reimers, N. & Gurevych, I. (2019).  
   **Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.**

2. Devlin, J., Chang, M.-W., Lee, K. & Toutanova, K. (2018).  
   **BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding.**

3. pgvector — PostgreSQL vector similarity search extension.

4. Django REST Framework documentation.

5. React documentation.

6. PostgreSQL documentation.

7. OpenAI API documentation.

8. JSON Web Token (JWT) documentation.

---

# 👩‍💻 Project Information

**Project Name:** CampusLens AI  
**Project Type:** Final Year Project  
**Domain:** Artificial Intelligence & Machine Learning  
**Application Area:** Recruitment and Career Recommendation

**Student:** Simranjeet Kaur  
**University:** Kurukshetra University  
**Academic Year:** 2026–2027

---

# ⚖️ Disclaimer

CampusLens AI is an academic prototype intended to demonstrate the practical application of NLP, vector embeddings, semantic search, LLM integration, and full-stack software development in recruitment.

The system is designed to assist candidates and recruiters.

It is **not intended to replace human decision-making in hiring** and should not be used as the sole basis for recruitment decisions.

---

# ⭐ Project Status

**Current Stage:** Development

CampusLens AI is being developed incrementally according to the final-year project synopsis.

Future updates will include implementation details, screenshots, evaluation results, testing results, and deployment information after those components have actually been completed.