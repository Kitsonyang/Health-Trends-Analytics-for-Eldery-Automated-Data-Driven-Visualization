# Nursing Home Analytics Dashboard

A production-ready healthcare analytics platform that combines Power BI embedded dashboards with machine learning for patient clustering and risk assessment. It supports CSV data import, symptom/category management, and automated dataset refreshes.



## Overview

The system provides secure authentication, robust CSV import with validation/mapping, ML-driven insights, and embedded Power BI visualizations to accelerate analytics delivery for care homes.

## Features

### Dashboard
- **Power BI Dashboard**: Interactive embedded analytics
- **Refresh History**: View Power BI refresh history and quota tracking

### Data Management (Admin Only)
- **Import Data**: CSV upload with validation and mapping
- **Symptoms Analysis**: Category insights and management

### AI & Analytics
- **Machine Learning**: Patient clustering and risk assessment predictions

## Tech Stack

- Frontend: React + TypeScript + Vite (served by Nginx)
- Backend: FastAPI (Python)
- Database: MySQL 8.x (PyMySQL)
- ML: scikit-learn, pandas, numpy
- Visualization: Power BI Embedded



## 📁 Project Structure

```
dashboard-powerbi/
├── backend/           # FastAPI routes, models, services, init SQL
│   ├── scripts/       # Utility scripts (get_powerbi_ids.py)
│   ├── data/sql/      # Database initialization scripts
│   └── requirements.txt
├── frontend/          # React app, Vite build, Nginx config
│   ├── src/           # React source code
│   └── package.json
├── docker-compose.yml # Docker orchestration
├── .env.example       # Environment variables template
└── README.md          # This file
```

## 🌐Live Demo

 **Live Demo**: [https://oyy994.cn/](https://oyy994.cn/)

Experience the full functionality of the Nursing Home Analytics Dashboard with demo accounts:
- Admin: username `admin001`, password `admin001`
- User: username `user001`, password `user001`

## 👥 User Roles


| Feature | Admin | User |
|---------|-------|------|
| Power BI Dashboard | ✅ | ✅ |
| Refresh History | ✅ | ✅ |
| Import Data | ✅ | ❌ |
| Symptoms Analysis | ✅ | ❌ |
| Machine Learning | ✅ | ✅ |


## 🚀 Deployment (Docker – Recommended)

### Prerequisites: Install Docker

**Windows:**
1. Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
2. Run installer as Administrator
3. Enable WSL 2 and restart when prompted

**Mac:**
1. Download [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/) (choose Apple Silicon or Intel version)
2. Install and launch from Applications
3. Follow setup wizard

**Verify installation:**
```bash
docker --version
docker-compose --version
```

### Step 1: Create Environment File
Create `.env` file at project root:
```env
# ==========================
# Frontend Settings
# Max upload size in MB for frontend (keep in sync with Nginx settings)
VITE_MAX_UPLOAD_MB=100

# ==========================
# Database (MySQL)
DB_HOST=localhost
DB_PORT=3306
DB_USER=dashboard_user
DB_PASSWORD=your_password
DB_NAME=dashboard

# ==========================
# Power BI Service Principal (Backend)
PBI_TENANT_ID=your_tenant_id
PBI_CLIENT_ID=your_client_id
PBI_CLIENT_SECRET=your_client_secret
PBI_WORKSPACE_ID=your_workspace_id
PBI_DATASET_ID=your_dataset_id
PBI_EMBED_URL=https://app.powerbi.com/view?r=...
```

### Step 2: Start Services
```bash
docker compose up -d --build
docker compose logs -f
```

### Step 3: Access Application
- **Frontend**: http://localhost:8088
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Step 4: Create User Accounts
- **First user**: Register at http://localhost:8088/register (automatically becomes admin)
- **Additional users**: Created by admin users

> **Note**: On first DB connection, the backend auto-creates the database and initializes tables using `backend/data/sql/dashboard.sql`.

## 🔧 Deployment (Separate Frontend & Backend)

### Backend (FastAPI)
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Frontend (Vite)
```bash
cd frontend
npm install
npm run dev
```

### Access Points
- **Frontend**: http://localhost:8088
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## ⚙️ Configuration Notes

1. **Database Setup**: Ensure MySQL is reachable with the provided `DB_*` values. The app creates the database and tables on first run if missing.
2. **Power BI Setup**: Power BI configuration requires Azure AD Service Principal with appropriate permissions.
3. **Docker Setup**: If using Docker, expose backend port `8000:8000` and ensure the app listens on `0.0.0.0:8000` inside the container.

## 🔍 Getting Power BI Configuration

### Step 1: Get Power BI Service Principal Credentials
You need to obtain these three values from Power BI admin portal:

1. **PBI_TENANT_ID**: Your Azure AD tenant ID
2. **PBI_CLIENT_ID**: Azure AD application (client) ID  
3. **PBI_CLIENT_SECRET**: Azure AD application client secret

**How to get them:**
1. Go to [Azure Portal](https://portal.azure.com) → Azure Active Directory
2. Navigate to "App registrations" → Create new registration
3. Note down the **Application (client) ID** and **Directory (tenant) ID**
4. Go to "Certificates & secrets" → Create new client secret
5. Copy the secret value (you won't see it again!)

### Step 2: Get Workspace and Dataset IDs
After configuring the Service Principal credentials, use the provided script:

```bash
cd backend
python -m scripts.get_powerbi_ids
```

**What the script does:**
1. Lists all available Power BI workspaces
2. Lists all datasets in the selected workspace
3. Provides the exact configuration values to add to your `.env` file

**Example output:**
```
PBI_WORKSPACE_ID=12345678-1234-1234-1234-123456789012
PBI_DATASET_ID=87654321-4321-4321-4321-210987654321
```

## 🛠️ Troubleshooting

1. **Docker not starting**: Restart Docker Desktop, check WSL 2 (Windows) or virtualization (Mac)
2. **Port conflicts**: Check ports 8088/8000 are free
3. **DB connection fails**: Check `DB_*` credentials in `.env`
4. **Power BI auth fails**: Verify Service Principal permissions
5. **Permission denied**: Some features require admin privileges

## 📚 Additional Resources

- **Environment Variables**: See `.env.example` for complete configuration options
- **Docker Configuration**: Check `docker-compose.yml` for production settings
- **API Documentation**: Available at `http://localhost:8000/docs` when running
- **Power BI Admin Portal**: [https://app.powerbi.com/admin-portal](https://app.powerbi.com/admin-portal)

---
