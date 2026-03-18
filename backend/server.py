from typing import Literal

from dotenv import load_dotenv
import dotenv
import openai
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request
from pydantic import BaseModel
import os
from fastapi.middleware.cors import CORSMiddleware
import PyPDF2
import logging
from model_service import AppConfig, GenerationConfig, ModelConfig, Generator, QuestionTaskConfig


load_dotenv()
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.1:8b")


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
    question: list[str]
    answers: dict[str, str]

# Root endpoint - returns server status
@app.get("/")
async def root():
    return {"status": "Server is running"}

# AI questions endpoint - POST only
@app.post("/api/ai/generate_questions")
async def generate_questions(data: TopicRequest):
    logger.info(f"Received request: topic={data.topic_name}, level={data.level}")
    
    try:
        configuration= AppConfig(
        model=ModelConfig(model_name=MODEL_NAME),  # Use environment variable or default to local Ollama model
        generation=GenerationConfig(),
        task=QuestionTaskConfig(topic=data.topic_name, level=data.level)
        )
        logger.info(configuration.task.level)
        generator = Generator(configuration)
        generated_questions = generator.generate_questions()
        if not generated_questions:
            raise HTTPException(status_code=404, detail="No questions were generated")
        return {"questions": generated_questions}
        
    except Exception as e:
        print(f"Error generating questions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/generate_feedback")
async def generate_feedback(data: FeedbackRequest):
    logger.info(f"Received {len(data.question)} questions for feedback")
    
    try:
        # Initialize generator
        configuration = AppConfig(
            model=ModelConfig(model_name=MODEL_NAME),
            generation=GenerationConfig(),
            task=QuestionTaskConfig()
        )
        generator = Generator(configuration)
        
        feedback_reports = []

        # 2. Loop through each question and its corresponding answer
        for index, question_text in enumerate(data.question):
            # Get the user's answer using the index, default to empty string if missing
            user_answer = data.answers.get(str(index), "") or "No answer provided."
            
            # Call AI logic for this specific pair
            # generator returns an object/dict with 'feedback' and 'score'
            result = generator.generate_feedback(question_text, user_answer)
            feedback_reports.append(result)

        # 3. Return the array frontend is expecting: { "feedback_reports": [...] }
        return {"feedback_reports": feedback_reports}
        
    except Exception as e:
        logger.error(f"Error generating feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
