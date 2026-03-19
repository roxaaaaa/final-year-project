from typing import Literal
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import logging, os
from model_service import AppConfig, GenerationConfig, ModelConfig, QuestionGenerator, DataConfig, FeedbackGenerator

load_dotenv()
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.1:8b")
CHAGPT_MODEL = os.getenv("CHAGPT_MODEL", "gpt-5.4-nano")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Create FastAPI app
app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log raw request body and validation errors to help debug 422 responses."""
    body_bytes = await request.body()
    try:
        body_text = body_bytes.decode()
    except Exception:
        body_text = str(body_bytes)

    print("DEBUG: RequestValidationError - raw body:", body_text)
    print("DEBUG: RequestValidationError - errors:", exc.errors())

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


# Pydantic model for request data
class TopicRequest(BaseModel):
    topic_name: str
    level: Literal["higher", "ordinary"]

class FeedbackRequest(BaseModel):
    question: str
    answer: str
    level: Literal["higher", "ordinary"]

# Root endpoint - returns server status
@app.get("/")
async def root():
    return {"status": "Server is running"}


@app.post("/api/ai/generate_questions")
async def generate_questions(data: TopicRequest):
    """Generate exam questions for a given topic and level."""
    logger.info(f"Received request: topic={data.topic_name}, level={data.level}")
    
    try:
        # Create config with request data
        config = AppConfig(
            model=ModelConfig(model_name=MODEL_NAME, api_key="ollama"),
            generation=GenerationConfig(),
            data=DataConfig(topic=data.topic_name, level=data.level)
        )
        
        generator = QuestionGenerator(config)
        generated_questions = generator.generate_questions()
        
        if not generated_questions:
            raise HTTPException(status_code=404, detail="No questions were generated")
        
        return {"questions": generated_questions, "count": len(generated_questions)}
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating questions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
@app.post("/api/ai/generate_feedback")
async def generate_feedback(content: FeedbackRequest):
    """Generate feedback for a student answer."""
    logger.info(f"Received feedback request for level: {content.level}")
    
    try:
        # Create config with request data
        config = AppConfig(
            model=ModelConfig(model_name=CHAGPT_MODEL, base_url = ""),
            generation=None,
            data=DataConfig(
                question=content.question,
                answer=content.answer,
                level=content.level
            )
        )
        generator = FeedbackGenerator(config)
        feedback = generator.generate_feedback()
        
        return {"feedback": feedback}
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))
 
# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
  