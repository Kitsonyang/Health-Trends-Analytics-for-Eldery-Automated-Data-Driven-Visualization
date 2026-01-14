# Overview
This dashboard is part of a larger Health Trends Analytics for Older People capstone project. It focuses on transforming fragmented aged-care health data into actionable insights through:
1. Interactive Power BI dashboards
2. Machine learning–based patient clustering and risk prediction
3. Secure backend services for data processing and analytics

# Key Features  
Dashboard
1. Embedded Power BI Dashboard for interactive analytics 
2. Population-level and resident-level health trend visualisation
3. Dataset refresh tracking and history

Data Management (Admin Role)
1. CSV data upload with validation and column mapping
2. Symptom and category analysis support
3. Controlled ingestion workflow to prevent data corruption

AI & Analytics
1. Machine Learning: Patient clustering and risk assessment predictions

Tech Stack
1. Frontend: React + TypeScript + Vite (served via Nginx)
2. Backend: FastAPI (Python)
3. Database: MySQL 8.x (PyMySQL)
4. Machine Learning: scikit-learn, pandas, numpy
5. Visualisation: Microsoft Power BI (Embedded)
6. Deployment: Docker & Docker Compose (local)

## Project Structure

- `dashboard/`
  - `backend/` – FastAPI routes, services, ML integration  
    - `scripts/` – Utility scripts (e.g., Power BI ID retrieval)  
    - `data/sql/` – Database initialization scripts  
    - `requirements.txt`
  - `frontend/` – React application and Nginx config  
    - `src/` – React source code  
    - `package.json`
  - `docker-compose.yml` – Local container orchestration
  - `.env.example` – Environment variable template
  - `README.md` – This documentation

## Installation

This dashboard is designed to be run **locally on PC or Mac**.  
A live online demo is not available as the deployment server has expired.

---

### 1️⃣ Prerequisites

Before installation, ensure the following are installed:

- **Docker Desktop**
  - Windows / macOS: https://www.docker.com/products/docker-desktop
- **Power BI account**
  - Required for Power BI Embedded access
- **Power BI Desktop** (Windows only – recommended)
  - macOS users can access Power BI via browser (Power BI Service)

Verify Docker installation:
```bash
docker --version
docker compose version
``` 
### 2️⃣ Clone the Repository
```bash
git clone https://github.com/Kitsonyang/Health-Trends-Analytics-for-Elderly-Automated-Data-Driven-Visualization.git
cd Health-Trends-Analytics-for-Elderly-Automated-Data-Driven-Visualization/dashboard
```
### 3️⃣ Set up Environment
```bash
# 
# Frontend Settings
# Max upload size in MB for frontend (keep in sync with Nginx settings)
VITE_MAX_UPLOAD_MB=100

# 
# Database (MySQL)
DB_HOST=localhost
DB_PORT=3306
DB_USER=dashboard_user
DB_PASSWORD=your_password
DB_NAME=dashboard

# ==
# Power BI Service Principal (Backend)
PBI_TENANT_ID=your_tenant_id
PBI_CLIENT_ID=your_client_id
PBI_CLIENT_SECRET=your_client_secret
PBI_WORKSPACE_ID=your_workspace_id
PBI_DATASET_ID=your_dataset_id
PBI_EMBED_URL=https://app.powerbi.com/view?r=...
```

### 4️⃣ Start Services with Docker
```bash
docker compose up -d --build
docker compose logs -f
```

### 5️⃣ Access the Application

Once containers are running:

1. Frontend UI: http://localhost:8088

2. Backend API: http://localhost:8000

3. API Documentation (Swagger): http://localhost:8000/docs

On first startup, the backend automatically:

1. "Creates the database"

2. "Initializes tables using SQL scripts in backend/data/sql/"


## 🔍 Getting Power BI Configuration

### Step 1: Get Power BI Service Principal Credentials
You need to obtain these three values from Power BI admin portal:
1. PBI_TENANT_ID: Your Azure AD tenant ID
2. PBI_CLIENT_ID: Azure AD application (client) ID
3. PBI_CLIENT_SECRET: Azure AD application client secret

How to get them:
1. Go to Azure Portal → Azure Active Directory
2. Navigate to "App registrations" → Create new registration
3. Note down the Application (client) ID and Directory (tenant) ID
4. Go to "Certificates & secrets" → Create new client secret
5. Copy the secret value (you won't see it again!)

### Step 2: Get Workspace and Dataset IDs
After configuring the Service Principal credentials, use the provided script:
```bash
cd backend
python -m scripts.get_powerbi_ids
```

### What the script does:
1. Lists all available Power BI workspaces
2. Lists all datasets in the selected workspace
3. Provides the exact configuration values to add to your .env file

### Example output:
```bash
PBI_WORKSPACE_ID=12345678-1234-1234-1234-123456789012
PBI_DATASET_ID=87654321-4321-4321-4321-210987654321
```
