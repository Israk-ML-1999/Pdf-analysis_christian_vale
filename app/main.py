from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware 
from app.config import settings
from app.Pdf import router as pdf_router

app = FastAPI(
    title="Government Tender Proposal Generator API",
    description="""
    AI-Powered Government Tender Analysis and Proposal Generation System
    
    """,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Include PDF router
app.include_router(pdf_router)

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - API information and available endpoints
    """
    return {
        "service": "Government Tender Proposal Generator API",
        "version": settings.APP_VERSION,
        "description": "AI-powered tender analysis and proposal generation",
        "model": "Google Gemini 2.5 Flash",
        "endpoints": {
            "documentation": {
                "swagger_ui": "/docs",
                "redoc": "/redoc"
            },
            "main_endpoints": {
                "analyze_tender": {
                    "path": "/pdf/analyze",
                    "method": "POST",
                    "description": "Upload tender PDF and generate proposal"
                },
                "health_check": {
                    "path": "/pdf/health",
                    "method": "GET",
                    "description": "Check service health"
                },
                "service_info": {
                    "path": "/pdf/info",
                    "method": "GET",
                    "description": "Get detailed service information"
                }
            }
        },
        "features": [
            "Upload up to 200-page tender documents",
            "Generate 15-20 page proposals",
            "Dynamic sections based on tender type",
            "10,000-12,000 word comprehensive content",
            "JSON formatted response"
        ],
        "quick_start": {
            "1": "Go to /docs for interactive API documentation",
            "2": "Use POST /pdf/analyze to upload your tender PDF",
            "3": "Receive comprehensive JSON proposal response"
        }
    }

@app.get("/health", tags=["System"])
async def health_check():
    """
    General system health check endpoint
    """
    return {
        "status": "healthy",
        "service": "Government Tender Proposal Generator API",
        "version": settings.APP_VERSION,
        "components": {
            "api": "operational",
            "pdf_service": "operational",
            "ai_model": "Gemini 2.5 Flash"
        }
    }