import openai
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware
import PyPDF2


load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Initialize OpenAI client
open_ai_key = os.getenv("OPEN_AI_KEY")
if not open_ai_key:
    raise ValueError("OPEN_AI_KEY environment variable is not set. Please set it in your .env file.")
client = openai.OpenAI(api_key=open_ai_key)

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
    level: str
    paper: str = None 

# PDF processing functions
def get_pdf_path( level, paper=None):
    """Map subject/level to file path"""
    base = os.path.join(os.path.dirname(__file__), "materials")
    if level == "higher":
        return os.path.join(base, "agriculture", "higher level", "last papers", "LC024ALP000EV.pdf")
    else:
        return os.path.join(base, "agriculture", "ordinary level", "last papers", "LC024GLP000EV.pdf")

def extract_text_by_rules(pdf_path, start_page=0, skip_first_page=False, stop_word=None):
    """Extract text from PDF with specific rules"""
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        text = ""
        pages = reader.pages
        if skip_first_page:
            pages = pages[1:]
        else:
            pages = pages[start_page:]
        for page in pages:
            page_text = page.extract_text()
            if stop_word and stop_word in page_text:
                break
            text += page_text
        return text

# Root endpoint - returns server status
@app.get("/")
async def root():
    return {"status": "Server is running"}

# AI questions endpoint - POST only
@app.post("/api/ai/generate_questions")
async def generate_questions(data: TopicRequest):
    print(f"Received request: topic={data.topic_name}, level={data.level}")
    
    try:
        # Determine the correct PDF path using the requested level and optional paper
        pdf_path = get_pdf_path(data.level, data.paper)
        if not pdf_path:
            raise HTTPException(status_code=404, detail="Missing path for agriculture paper")
        else:
            past_exam_text = extract_text_by_rules(pdf_path, skip_first_page=True, stop_word="Do not write on this page")
            combined_text = past_exam_text
        
        # Generate AI questions
        prompt = (
            f"You are an experienced Leaving Certificate teacher. "
            f"Here is past exam paper for agriculture science ({data.level}):\n\n"
            f"{combined_text}\n\n"
            f"Write 3 structured exam-style open-ended questions about the topic: '{data.topic_name}'.\n"
            f"Each question should have two or more parts. Format them as follows:\n\n"
            f"1. [First question with parts]\n\n"
            f"2. [Second question with parts]\n\n"
            f"3. [Third question with parts]\n\n"
            f"Make sure each question is numbered and has a blank line between questions."
        )
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return {"questions": response.choices[0].message.content}
        
    except Exception as e:
        print(f"Error generating questions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)