from typing import Literal, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from model_service import (
    AppConfig, GenerationConfig, ModelConfig, QuestionGenerator, 
    DataConfig, FeedbackGenerator, VideoGenerator
)

load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME", "llama3.1:8b")
CHAGPT_MODEL = os.getenv("CHAGPT_MODEL", "gpt-4o-mini")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
DID_API_KEY = os.getenv("DID_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Agricultural Science Exam Assistant",
    description="API for generating exam questions and feedback with D-ID avatar videos",
    version="1.0.0"
)

# Exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log raw request body and validation errors to help debug 422 responses."""
    body_bytes = await request.body()
    try:
        body_text = body_bytes.decode()
    except Exception:
        body_text = str(body_bytes)

    logger.error(f"Validation Error - Body: {body_text}, Errors: {exc.errors()}")

    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "raw_body": body_text},
    )

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PYDANTIC MODELS
class TopicRequest(BaseModel):
    """Request model for generating exam questions."""
    topic_name: str
    level: Literal["higher", "ordinary"] = "ordinary"

class FeedbackRequest(BaseModel):
    """Request model for generating feedback."""
    question: str
    answer: str
    level: Literal["higher", "ordinary"] = "ordinary"
    use_video: bool = True  # Whether to generate D-ID video

class VideoStatusRequest(BaseModel):
    """Request model for checking video status."""
    clip_id: str

class PresentersResponse(BaseModel):
    """Response model for available presenters."""
    presenters: list
    message: str


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "status": "Server is running",
        "service": "Agricultural Science Exam Assistant",
        "d_id_configured": bool(DID_API_KEY)
    }


@app.get("/health", tags=["Health"])
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "ollama_available": bool(OLLAMA_BASE_URL),
        "openai_available": bool(CHAGPT_MODEL),
        "d_id_available": bool(DID_API_KEY)
    }


@app.post("/api/ai/generate_questions", tags=["Questions"])
async def generate_questions(data: TopicRequest):
    """
    Generate exam questions for a given topic and level.
    
    Args:
        data: TopicRequest with topic_name and level
    
    Returns:
        JSON with generated questions and count
    """
    logger.info(f"Generating questions: topic={data.topic_name}, level={data.level}")
    
    try:
        config = AppConfig(
            model=ModelConfig(model_name=MODEL_NAME, api_key="ollama"),
            generation=GenerationConfig(),
            data=DataConfig(topic=data.topic_name, level=data.level)
        )
        
        generator = QuestionGenerator(config)
        generated_questions = generator.generate_questions()
        
        if not generated_questions:
            raise HTTPException(status_code=404, detail="No questions were generated")
        
        return {
            "questions": generated_questions,
            "count": len(generated_questions),
            "level": data.level,
            "topic": data.topic_name
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating questions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/generate_feedback", tags=["Feedback"])
async def generate_feedback(content: FeedbackRequest):
    """
    Generate feedback for a student answer, optionally with D-ID avatar video.
    
    Args:
        content: FeedbackRequest with question, answer, level, and use_video flag
    
    Returns:
        JSON with feedback text and optional video URL
    """
    logger.info(f"Generating feedback: level={content.level}, use_video={content.use_video}")
    
    try:
        config = AppConfig(
            model=ModelConfig(model_name=CHAGPT_MODEL, base_url=None),
            generation=None,
            data=DataConfig(
                question=content.question,
                answer=content.answer,
                level=content.level
            )
        )
        
        # Check if video is requested and D-ID is configured
        use_video = content.use_video and bool(DID_API_KEY)
        
        if use_video:
            generator = FeedbackGenerator(config, use_video=True)
            result = generator.generate_feedback_with_video()
            
            return {
                "feedback": result["feedback_text"],
                "video_url": result["video_url"],
                "clip_id": result["clip_id"],
                "has_video": result["video_url"] is not None
            }
        else:
            generator = FeedbackGenerator(config, use_video=False)
            feedback = generator.generate_feedback()
            
            return {
                "feedback": feedback,
                "video_url": None,
                "clip_id": None,
                "has_video": False
            }
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/d-id/video-status/{clip_id}", tags=["D-ID"])
async def get_video_status(clip_id: str):
    """
    Check the status of a D-ID video clip.
    
    Args:
        clip_id: The D-ID clip ID
    
    Returns:
        JSON with video status and result URL if ready
    """
    if not DID_API_KEY:
        raise HTTPException(status_code=503, detail="D-ID not configured")
    
    try:
        video_gen = VideoGenerator()
        status = video_gen.get_video_status(clip_id)
        return status
        
    except Exception as e:
        logger.error(f"Error checking video status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/d-id/presenters", tags=["D-ID"])
async def get_presenters():
    """
    Get list of available D-ID avatar presenters.
    
    Returns:
        JSON with list of available presenters
    """
    if not DID_API_KEY:
        return {
            "presenters": [
                {
                    "id": "v2_public_Amber@0zSz8kflCN",
                    "name": "Amber",
                    "gender": "Female"
                },
                {
                    "id": "v2_public_Adam@0GLJgELXjc",
                    "name": "Adam",
                    "gender": "Male"
                }
            ],
            "message": "D-ID API not configured. Showing default presenters.",
            "configured": False
        }
    
    try:
        video_gen = VideoGenerator()
        presenters = video_gen.get_presenters()
        return {
            "presenters": presenters,
            "configured": True
        }
        
    except Exception as e:
        logger.error(f"Error fetching presenters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Run the app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)