# 📄 CV Analyser

**CV Analyser** is an AI-powered full-stack web application designed to help university students, graduates, and job seekers tailor their CVs and cover letters for target job descriptions. By automated ATS-oriented suitability scoring and actionable feedback, CV Analyser boosts interview callback rates while saving hours of manual editing.

---

## Features

- **User Authentication**: Secure email & password registration and login powered by JWT & Bcrypt.
- **CV Management**: Upload, preview, and manage `.txt` or `.md` CV files with metadata stored in SQL and actual files hosted in scalable Object Storage (S3 / MinIO).
- **AI Suitability Analysis**: Instant match score between your CV and job descriptions, complete with pinpointed feedback and concrete improvement suggestions.
- **Personalized Cover Letter Generator**: Generate tailored cover letters instantly using AI aligned directly with the target position's requirements.
- **Redis Caching**: Frequently accessed CV content is cached in Redis for fast retrieval and reduced object storage fetch latency.
- **Docker Support**: Containerized environment for simplified local development and deployment.

---

## 🛠️ Tech Stack

### Frontend
- **Framework**: [React 19](https://react.dev/)
- **Build Tool**: [Vite](https://vitejs.dev/)
- **Routing**: [React Router v7](https://reactrouter.com/)

### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+)
- **Server**: Uvicorn
- **Database / ORM**: SQLAlchemy (SQLite for development / PostgreSQL ready)
- **Object Storage**: AWS S3 / MinIO (via `boto3`)
- **AI Integration**: OpenAI API
- **Caching**: Redis

### Infrastructure & DevOps
- **Containerization**: Docker & Docker Compose

---

## Project Structure

```text
CVanalyser/
├── backend/
│   ├── app/ (or routers, models, schemas)
│   ├── auth.py          # Authentication handlers (JWT & password hashing)
│   ├── database.py      # SQLAlchemy database session & engine
│   ├── models.py        # Database tables (Users, UserFiles)
│   ├── main.py          # FastAPI application entrypoint
│   ├── schemas.py       # Pydantic schemas
│   ├── requirements.txt # Python dependencies
│   └── Dockerfile       # Backend container definition
├── frontend/
│   ├── src/             # React components, pages, & assets
│   ├── index.html       # HTML entrypoint
│   ├── package.json     # Frontend dependencies & scripts
│   ├── vite.config.js   # Vite configuration
│   └── Dockerfile       # Frontend container definition
├── docker-compose.yml   # Orchestration for Backend, Frontend, and Redis
├── spec.md              # Project technical specification
├── nextsteps.md         # Planned feature roadmap
└── README.md            # Project documentation
```

---

## 🚀 Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/)
*OR*
- **Python 3.10+** & **Node.js 18+** installed locally.

---

### Option 1: Quickstart with Docker Compose (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/CVanalyser.git
   cd CVanalyser
   ```

2. **Set up Environment Variables**:
   Copy `.example.env` to `.env` in the `backend/` directory and update your configuration .
   ```bash
   cp .example.env backend/.env
   ```

3. **Start the containers**:
   ```bash
   docker-compose up --build
   ```

4. **Access the Application**:
   - **Frontend**: `http://localhost:5173`
   - **Backend API Docs**: `http://localhost:8000/docs`
   - **Redis Cache**: `localhost:6379`

---

### Option 2: Local Development without Docker

#### 1. Backend Setup

```bash
# Navigate to backend
cd backend

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn main:app --reload --port 8000
```

#### 2. Frontend Setup

```bash
# Open a new terminal and navigate to frontend
cd frontend

# Install Node modules
npm install

# Start Vite dev server
npm run dev
```

---

## Environment Variables

Make sure to configure the following in `backend/.env`:

| Variable | Description |
| :--- | :--- |
| `BEDROCK_API_KEY` | Bedrock API key for CV analysis & cover letter generation |
| `BEDROCK_BASE_URL` | Bedrock API base URL |
| `DATABASE_URL` | Database connection string (defaults to `sqlite:///./sql_app.db`) |
| `REDIS_URL` | Redis connection URL (defaults to `redis://localhost:6379/0`) |
| `SECRET_KEY` | JWT signing secret key |
| `ALGORITHM` | JWT hashing algorithm (defaults to `HS256`) |
| `AWS_ACCESS_KEY_ID` | Object Storage access key |
| `AWS_SECRET_ACCESS_KEY` | Object Storage secret key |
| `S3_BUCKET_NAME` | Storage bucket name for uploaded CV files |

---

## 🗺️ Roadmap & Future Enhancements

- ☁️ **Cloud Deployment**: Deployment on AWS EC2 with automated CI/CD pipeline.

---

## 📜 License

This project is open-source under the [MIT License](LICENSE).
