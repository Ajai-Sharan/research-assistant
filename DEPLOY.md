# Deployment Guide: AI Research Paper Assistant

This guide explains how to run and deploy the AI Research Paper Assistant with the new React + TypeScript animated frontend.

---

## 📋 Prerequisites

Before running the application, make sure you have the following installed on your machine:
- **Python**: Version 3.10+
- **Node.js**: Version 20+ (with npm/npx)
- **GitHub Token**: You need a token for GitHub Models (`GITHUB_TOKEN` environment variable).

---

## 🛠️ Configuration & Environment Variables

Create or set the following environment variables:

| Variable | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `GITHUB_TOKEN` | **Yes** | - | Your GitHub Models API Token |
| `GITHUB_MODEL` | No | `gpt-4o` | The model identifier to use on the OpenAI client |
| `BACKEND_URL` | No | `http://localhost:8000` | The backend address. (If served via Single-Server Deploy, this defaults to the origin address automatically) |

Example of setting variables in your terminal:
```bash
export GITHUB_TOKEN=ghp_your_token_here
export GITHUB_MODEL=gpt-4o
```

---

## 🚀 Deployment Options

Choose one of the two options below to run or deploy the application:

### 1️⃣ Option 1: Single-Server Deployment (Recommended for Production)

In this mode, the FastAPI backend hosts and serves the compiled React application directly. This is the simplest and most performant deployment method, removing the need to manage CORS or run separate frontend containers.

#### Step 1: Build the React Frontend
Navigate to the `frontend/` folder, install dependencies, and compile the assets into static HTML/CSS/JS:
```bash
cd frontend
npm install
npm run build
```
This compiles the production assets into `frontend/dist`.

#### Step 2: Launch the FastAPI server
Return to the project root and start the backend using `uvicorn`:
```bash
cd ..
# Activate your python virtual environment
source .venv/bin/activate
# Install requirements (if not done already)
pip install -r requirements.txt
# Run the FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
FastAPI will detect the built files in `frontend/dist` and serve them from `http://localhost:8000/`. You can now open your browser and navigate directly to this address.

---

### 2️⃣ Option 2: Dual-Server Setup (Recommended for Development)

In this mode, the backend runs on `localhost:8000` while the React Vite server runs on `localhost:5173`. Hot Module Replacement (HMR) is enabled, making it easy to test changes.

#### Terminal 1 — Start the Backend Server
```bash
# Activate your virtual environment and set token
source .venv/bin/activate
export GITHUB_TOKEN=ghp_your_token_here

# Run backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Terminal 2 — Start the React Vite Development Server
```bash
cd frontend
# Install dependencies
npm install

# Run frontend in dev mode
npm run dev
```

Open your browser at [http://localhost:5173](http://localhost:5173) to see the application. The React application will automatically proxy API calls to the backend on port 8000.

---

## 📦 Docker / Container Deployment

To pack this application into a single container for services like AWS, GCP, or Render:

1. Create a `Dockerfile` at the root of the workspace:
   ```dockerfile
   # Stage 1: Build Frontend
   FROM node:20-alpine AS frontend-builder
   WORKDIR /frontend
   COPY frontend/package*.json ./
   RUN npm install
   COPY frontend/ ./
   RUN npm run build

   # Stage 2: Serve Backend & Frontend
   FROM python:3.10-slim
   WORKDIR /workspace
   COPY requirements.txt ./
   RUN pip install --no-cache-dir -r requirements.txt
   
   COPY app/ ./app/
   COPY --from=frontend-builder /frontend/dist ./frontend/dist
   
   ENV GITHUB_TOKEN=""
   EXPOSE 8000
   
   CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. Build and run the docker container:
   ```bash
   docker build -t research-assistant .
   docker run -p 8000:8000 -e GITHUB_TOKEN="ghp_xxx" research-assistant
   ```
