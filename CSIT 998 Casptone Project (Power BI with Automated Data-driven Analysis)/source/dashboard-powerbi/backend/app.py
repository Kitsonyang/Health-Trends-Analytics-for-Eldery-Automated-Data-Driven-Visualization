"""
Nursing Home Analytics Platform - FastAPI Application

Main application entry point for the backend API server. Provides endpoints for:
- User authentication and authorization (session-based with bearer tokens)
- CSV data import and validation
- Symptom categorization and management
- Machine learning predictions (clustering and risk assessment)
- Power BI dataset refresh orchestration
- Healthcare analytics data access

Architecture:
- Modular router organization for separation of concerns
- CORS enabled for cross-origin frontend communication
- MySQL database for data persistence
- Integration with Azure Power BI REST API
- Role-based access control (RBAC) for admin-only endpoints

Deployment:
- Development: Run via `python app.py` or `uvicorn app:app --reload`
- Production: Use Gunicorn/Uvicorn with Docker container orchestration
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from utils.shared import ensure_schema_initialized

# Import modular route handlers
from routes.health_routes import router as health_router
from routes.auth_routes import router as auth_router
from routes.import_routes import router as import_router
from routes.data_routes import router as data_router
from routes.categories_routes import router as categories_router
from routes.symptoms_routes import router as symptoms_router
from routes.cluster_usage_routes import router as cluster_usage_router
from routes.cluster_display_routes import router as cluster_display_router
from routes.risk_routes import router as risk_router
from routes.powerbi_routes import router as powerbi_router
from routes.cleanup_routes import router as cleanup_router

# Initialize FastAPI application with metadata
app = FastAPI(
    title="Nursing Home Analytics API",
    version="1.0.0",
    description="Backend API for healthcare analytics dashboard with ML predictions and Power BI integration"
)

# Configure CORS middleware for frontend communication
# Note: In production, replace "*" with specific allowed origins for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,        # Required for cookie-based auth (if implemented)
    allow_methods=["*"],           # Allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],           # Allow Authorization, Content-Type, etc.
)

# Ensure DB schema exists (run once on cold start if database is empty)
try:
    ensure_schema_initialized()
except Exception:
    # Defer to routes to raise meaningful errors if DB remains uninitialized
    pass

# Register route modules with application
# Order matters for route precedence (more specific routes should come first)
app.include_router(health_router)           # Health check endpoints
app.include_router(auth_router)             # Authentication and user management
app.include_router(import_router)           # CSV import and validation
app.include_router(data_router)             # Data retrieval endpoints
app.include_router(categories_router)       # Symptom category management
app.include_router(symptoms_router)         # Symptom analysis endpoints
app.include_router(cluster_usage_router)    # ML clustering predictions
app.include_router(cluster_display_router)  # Cluster visualization data
app.include_router(risk_router)             # Risk assessment ML predictions
app.include_router(powerbi_router)          # Power BI integration
app.include_router(cleanup_router)          # File cleanup management

# Development server entry point
# Production deployments should use Gunicorn/Uvicorn workers instead
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,                # Hot reload for development
        log_level="info"
    )
