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
- **Database / ORM**: SQLAlchemy with PostgreSQL 16 (production) or SQLite (development)
- **Object Storage**: AWS S3 (via `boto3`) with Server-Side Encryption (AES256)
- **AI Integration**: AWS Bedrock Mantle / OpenAI API
- **Caching**: Redis
- **Reverse Proxy**: Nginx (production gateway)

### Infrastructure & DevOps
- **Containerization**: Docker & Docker Compose (`docker-compose.prod.yml`)
- **Web Server**: Nginx (Reverse Proxy, SSL, Gzip, SPA routing)
- **WSGI / ASGI**: Gunicorn with Uvicorn workers

---

## 🚀 Getting Started

### Local Development (Quickstart)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/CVanalyser.git
   cd CVanalyser
   ```

2. **Configure environment**:
   ```bash
   cp .example.env backend/.env
   ```

3. **Start local development containers**:
   ```bash
   docker-compose up --build
   ```

---

## 🌐 Production Deployment on Local Ubuntu Server

A complete provisioning script and production Docker Compose configuration are provided:

1. **Prerequisites & S3 Setup**:
   - Follow the detailed guide in [`docs/AWS_S3_IAM_GUIDE.md`](docs/AWS_S3_IAM_GUIDE.md) to set up your S3 bucket and IAM user.

2. **Automated Server Provisioning**:
   On your Ubuntu 22.04 / 24.04 server, clone the repository and run:
   ```bash
   sudo ./scripts/setup_ubuntu_server.sh
   ```
   This will:
   - Install Docker Engine and Docker Compose.
   - Configure UFW firewall (allowing ports 22, 80, 443).
   - Generate secure random secrets into `.env.prod`.
   - Register a `systemd` service (`cvanalyser.service`) to start on boot.

3. **Configure Production Credentials**:
   Edit `.env.prod` to provide your S3 credentials:
   ```bash
   nano .env.prod
   ```

4. **Start the Production Stack**:
   ```bash
   sudo systemctl start cvanalyser
   # Or manually:
   docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
   ```

5. **Access the Application**:
   - Web application: `http://<your-server-ip>` or `http://<your-domain>`
   - Healthcheck: `http://<your-server-ip>/api/health`

---

## 📜 License

This project is open-source under the [MIT License](LICENSE).
