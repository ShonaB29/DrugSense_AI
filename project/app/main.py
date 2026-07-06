from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import logging
from app.core.config import get_settings
from app.core.auth import authenticate_user, create_access_token
from app.models import Token, HealthCheckResponse
from app.api.prescriptions import router as prescriptions_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered prescription analysis and safety checking system",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HTTP Basic Auth for token endpoint
security = HTTPBasic()

# Include routers
app.include_router(prescriptions_router)


@app.get("/", response_model=HealthCheckResponse)
async def root():
    """Health check endpoint"""
    return HealthCheckResponse(
        status="healthy",
        version=settings.app_version,
        timestamp=datetime.utcnow().isoformat()
    )


@app.post("/token", response_model=Token)
async def login_for_access_token(credentials: HTTPBasicCredentials = Depends(security)):
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Detailed health check endpoint"""
    return HealthCheckResponse(
        status="healthy",
        version=settings.app_version,
        timestamp=datetime.utcnow().isoformat()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
