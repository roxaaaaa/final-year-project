"""AgriExamAI backend: REST API for exam questions, practice, feedback, and login."""

from typing import Literal, Optional, cast
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import asyncio
import logging
import os
from model_service import (
    AppConfig,
    GenerationConfig,
    ModelConfig,
    QuestionGenerator,
    DataConfig,
    FeedbackGenerator,
    VideoGenerator,
    DID_API_KEY,
    DID_AVATAR_ENABLED,
    did_avatar_permission_denied,
)

load_dotenv()

from security_settings import jwt_secret, session_secret

MODEL_NAME = os.getenv("MODEL_NAME", "llama3.1:8b")
CHATGPT_MODEL = os.getenv("CHATGPT_MODEL", "gpt-4o-mini")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def _cors_allow_origins() -> list[str]:
    """Same dev app may be opened as localhost or 127.0.0.1; browsers treat them as different origins."""
    from urllib.parse import urlparse

    base = FRONTEND_URL.rstrip("/")
    origins = {base}
    try:
        p = urlparse(base)
        if p.hostname == "localhost":
            origins.add(base.replace("://localhost", "://127.0.0.1", 1))
        elif p.hostname == "127.0.0.1":
            origins.add(base.replace("://127.0.0.1", "://localhost", 1))
    except Exception:
        pass
    # Vercel preview URLs, alternate domains, etc. (comma-separated, no trailing slash)
    for part in os.getenv("CORS_EXTRA_ORIGINS", "").split(","):
        u = part.strip().rstrip("/")
        if u:
            origins.add(u)
    return list(origins)


def _session_cookie_https_only() -> bool:
    # On HTTPS we send the session cookie only over secure connections. You can change this with env vars.
    explicit = os.getenv("SESSION_COOKIE_SECURE")
    if explicit is not None:
        return explicit.lower() in ("1", "true", "yes")
    return os.getenv("RENDER", "").lower() == "true"


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    logger.warning("OAuth Credentials missing! Sign-up and Login will fail.")
# Create FastAPI app
app = FastAPI(
    title="Agricultural Science Exam Assistant",
    description="API for generating exam questions, feedback, and D-ID avatar videos for practice",
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

    return JSONResponse(status_code=422, content={"detail": exc.errors()})

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret(),
    same_site="lax",
    https_only=_session_cookie_https_only(),
)

# Fail fast if JWT signing secret is missing (OAuth callback would otherwise return 500).
_ = jwt_secret()

# Trust X-Forwarded-Proto (etc.) from Render / reverse proxies so request.base_url uses https.
try:
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
except Exception as e:
    logger.warning("ProxyHeadersMiddleware not enabled: %s", e)

from routers.auth import router as auth_router
app.include_router(auth_router)
from routers.user import router as user_router
app.include_router(user_router)

from database import init_schema_sync

init_schema_sync()
logger.info("Database schema ready (create_all at import).")

class TopicRequest(BaseModel):
    """Request model for generating exam questions."""
    topic_name: str
    level: Literal["higher", "ordinary"] = "ordinary"

class FeedbackRequest(BaseModel):
    """Request model for generating feedback."""
    question: str
    answer: str
    level: Literal["higher", "ordinary"] = "ordinary"
    use_video: bool = True  # When true and DID_API_KEY is set, generate a D-ID Talk (MP4 URL).

class PracticeAttemptRequest(BaseModel):
    """Request model for saving practice attempt."""
    exam_id: int
    answers: dict  # {question_index: answer_text}

class FeedbackSubmissionRequest(BaseModel):
    """Request model for submitting feedback request."""
    exam_id: int
    question_index: int
    answer: str
    use_video: bool = True  # Request D-ID video when DID_API_KEY is configured.


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "status": "Server is running",
        "service": "Agricultural Science Exam Assistant",
        "d_id_configured": bool(DID_API_KEY),
        "d_id_avatar_enabled": DID_AVATAR_ENABLED,
        "google_oauth_configured": bool(GOOGLE_CLIENT_ID),
        "env": os.getenv("ENV", "development")
    }


@app.get("/health", tags=["Health"])
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "ollama_available": bool(OLLAMA_BASE_URL),
        "openai_available": bool(os.getenv("OPENAI_API_KEY")),
        "d_id_configured": bool(DID_API_KEY),
        "d_id_avatar_enabled": DID_AVATAR_ENABLED,
    }


from routers.user import get_current_user
from database import async_session, get_db
from models import User, PersonaEnum, GeneratedExam, PracticeAttempt, Feedback
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import Depends, Query
from fastapi.responses import Response
import json

from exam_export import build_exam_docx, build_exam_pdf, sanitize_download_filename

@app.post("/api/ai/generate_questions", tags=["Questions"])
async def generate_questions(
    data: TopicRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create questions for topic/level, save exam, enforce persona generation limits."""
    if not user.persona:
        raise HTTPException(status_code=400, detail="Persona must be selected before generating")

    # Generation limits per persona
    generation_limit = 3 if user.persona.value == "student" else 5
    
    # Check if user has reached their lifetime limit
    if user.generations_number >= generation_limit:
        raise HTTPException(
            status_code=429,
            detail=f"You have reached your generation limit. {generation_limit} generation(s) allowed for {user.persona.value}s."
        )

    # Determine number of questions based on persona
    num_questions = 3 if user.persona.value == "student" else 5

    #logger.info(f"Generating questions: topic={data.topic_name}, level={data.level}, user={user.id}, persona={user.persona.value}, num_questions={num_questions}")
    
    try:
        config = AppConfig(
            model=ModelConfig(model_name=MODEL_NAME, api_key="ollama"),
            generation=GenerationConfig(num_questions=num_questions),
            data=DataConfig(topic=data.topic_name, level=data.level)
        )
        
        generator = QuestionGenerator(config)
        generated_questions = generator.generate_questions()
        
        if not generated_questions:
            raise HTTPException(status_code=404, detail="No questions were generated")

        exam = GeneratedExam(
            user_id=user.id,
            topic=data.topic_name,
            level=data.level,
            questions=json.dumps(generated_questions),
        )
        db.add(exam)

        # Update user generation tracking
        user.generations_number += 1
        db.add(user)
        await db.commit()
        await db.refresh(user)
        await db.refresh(exam)

        return {
            "questions": generated_questions,
            "count": len(generated_questions),
            "level": data.level,
            "topic": data.topic_name,
            "status": "success",
            "generations_remaining": generation_limit - user.generations_number,
            "exam_id": exam.id,
        }
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error generating questions")
        raise HTTPException(status_code=500, detail="Failed to generate questions")

@app.get("/api/user/exams", tags=["User"])
async def get_user_exams(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List this user's saved exams (metadata only, not full question text)."""
    try:
        result = await db.execute(
            select(GeneratedExam).where(GeneratedExam.user_id == user.id).order_by(GeneratedExam.created_at.desc())
        )
        exams = result.scalars().all()
        
        exam_list = []
        for exam in exams:
            exam_list.append({
                "id": exam.id,
                "topic": exam.topic,
                "level": exam.level,
                "questions_count": len(json.loads(exam.questions)),
                "created_at": exam.created_at.isoformat(),
            })
        
        return {"exams": exam_list}
        
    except Exception as e:
        logger.error(f"Error retrieving user exams: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve exams")

@app.get("/api/exams/{exam_id}", tags=["Exams"])
async def get_exam_details(
    exam_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Return one exam with parsed questions if it belongs to the current user."""
    try:
        result = await db.execute(
            select(GeneratedExam).where(
                GeneratedExam.id == exam_id,
                GeneratedExam.user_id == user.id
            )
        )
        exam = result.scalar_one_or_none()
        
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        return {
            "id": exam.id,
            "topic": exam.topic,
            "level": exam.level,
            "questions": json.loads(exam.questions),
            "created_at": exam.created_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving exam details: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve exam details")


@app.get("/api/exams/{exam_id}/export", tags=["Exams"])
async def export_exam(
    exam_id: int,
    export_format: str = Query(..., alias="format", description="pdf or docx"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Teacher-only: stream PDF or Word for a saved exam."""
    if user.persona != PersonaEnum.teacher:
        raise HTTPException(
            status_code=403,
            detail="Exam export is only available for teacher accounts.",
        )

    fmt = (export_format or "").lower()
    if fmt not in ("pdf", "docx"):
        raise HTTPException(
            status_code=400,
            detail='Invalid format; use "pdf" or "docx".',
        )

    try:
        result = await db.execute(
            select(GeneratedExam).where(
                GeneratedExam.id == exam_id,
                GeneratedExam.user_id == user.id,
            )
        )
        exam = result.scalar_one_or_none()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")

        raw = json.loads(exam.questions)
        if not isinstance(raw, list) or not all(isinstance(q, str) for q in raw):
            raise HTTPException(status_code=500, detail="Invalid exam question data")

        if fmt == "docx":
            body = build_exam_docx(exam.topic, exam.level, raw)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            body = build_exam_pdf(exam.topic, exam.level, raw)
            media_type = "application/pdf"

        filename = sanitize_download_filename(exam.topic, exam.id, fmt)
        return Response(
            content=body,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid exam question data")
    except Exception as e:
        logger.error(f"Error exporting exam: {e}")
        raise HTTPException(status_code=500, detail="Failed to export exam")


@app.post("/api/practice/start", tags=["Practice"])
async def start_practice_attempt(
    request: Request,
    data: PracticeAttemptRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create or update draft answers for a user's exam."""
    try:
        # Check if exam exists and belongs to user
        result = await db.execute(
            select(GeneratedExam).where(
                GeneratedExam.id == data.exam_id,
                GeneratedExam.user_id == user.id
            )
        )
        exam = result.scalar_one_or_none()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")

        # Check if practice attempt already exists
        result = await db.execute(
            select(PracticeAttempt).where(
                PracticeAttempt.user_id == user.id,
                PracticeAttempt.generated_exam_id == data.exam_id
            )
        )
        attempt = result.scalar_one_or_none()

        if attempt:
            # Update existing attempt
            attempt.answers = json.dumps(data.answers)
            db.add(attempt)
        else:
            # Create new attempt
            attempt = PracticeAttempt(
                user_id=user.id,
                generated_exam_id=data.exam_id,
                answers=json.dumps(data.answers)
            )
            db.add(attempt)

        await db.commit()
        await db.refresh(attempt)

        return {"attempt_id": attempt.id, "status": "saved"}

    except Exception as e:
        logger.error(f"Error saving practice attempt: {e}")
        raise HTTPException(status_code=500, detail="Failed to save practice attempt")

@app.post("/api/feedback/generate", tags=["Feedback"])
async def generate_feedback(
    data: FeedbackSubmissionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Feedback for one question index; persists rows and optional D-ID talk id."""
    try:
        user_id = user.id
        # Get the exam to retrieve the question
        result = await db.execute(
            select(GeneratedExam).where(
                GeneratedExam.id == data.exam_id,
                GeneratedExam.user_id == user_id,
            )
        )
        exam = result.scalar_one_or_none()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")

        questions = json.loads(exam.questions)
        if data.question_index >= len(questions):
            raise HTTPException(status_code=400, detail="Invalid question index")

        question = questions[data.question_index]

        # OpenAI chat model + real API key (not the Ollama placeholder used for question gen)
        config = AppConfig(
            model=ModelConfig(model_name=CHATGPT_MODEL, base_url=None),
            generation=GenerationConfig(num_questions=1),
            data=DataConfig(
                topic=exam.topic,
                level=cast(Literal["higher", "ordinary"], exam.level),
                question=question,
                answer=data.answer,
            )
        )

        want_video = (
            data.use_video
            and bool(DID_API_KEY)
            and DID_AVATAR_ENABLED
            and not did_avatar_permission_denied()
        )
        talk_id: Optional[str] = None

        # Do not hold a pooled DB connection across OpenAI + D-ID (can exceed Neon/PgBouncer idle limits).
        await db.close()

        if want_video:
            generator = FeedbackGenerator(config, use_video=True)
            bundle = await asyncio.to_thread(generator.generate_feedback_with_video)
            feedback_result = bundle["feedback_text"]
            video_url = bundle.get("video_url")
            talk_id = bundle.get("talk_id")
            video_status = bundle.get("video_status") or ("completed" if video_url else "failed")
        else:
            generator = FeedbackGenerator(config, use_video=False)
            feedback_result = await asyncio.to_thread(generator.generate_feedback)
            video_url = None
            if data.use_video and not DID_API_KEY:
                video_status = "skipped"
            elif data.use_video and DID_API_KEY and not DID_AVATAR_ENABLED:
                video_status = "skipped"
            elif data.use_video and bool(DID_API_KEY) and DID_AVATAR_ENABLED and did_avatar_permission_denied():
                video_status = "skipped"
            else:
                video_status = "not_used"

        async with async_session() as db2:
            # Get or create practice attempt
            result = await db2.execute(
                select(PracticeAttempt).where(
                    PracticeAttempt.user_id == user_id,
                    PracticeAttempt.generated_exam_id == data.exam_id,
                )
            )
            attempt = result.scalar_one_or_none()

            if not attempt:
                attempt = PracticeAttempt(
                    user_id=user_id,
                    generated_exam_id=data.exam_id,
                    answers=json.dumps({data.question_index: data.answer}),
                )
                db2.add(attempt)
                await db2.commit()
                await db2.refresh(attempt)

            result = await db2.execute(
                select(Feedback).where(
                    Feedback.practice_attempt_id == attempt.id,
                    Feedback.question_index == data.question_index,
                )
            )
            existing_feedback = result.scalar_one_or_none()

            if existing_feedback:
                existing_feedback.feedback_text = feedback_result
                existing_feedback.video_url = video_url
                existing_feedback.video_status = video_status
                if talk_id:
                    existing_feedback.d_id_talk_id = talk_id
                db2.add(existing_feedback)
            else:
                feedback_entry = Feedback(
                    practice_attempt_id=attempt.id,
                    question_index=data.question_index,
                    feedback_text=feedback_result,
                    video_url=video_url,
                    video_status=video_status,
                    d_id_talk_id=talk_id,
                )
                db2.add(feedback_entry)

            await db2.commit()

        return {
            "feedback": feedback_result,
            "video_url": video_url,
            "video_status": video_status,
            "talk_id": talk_id,
        }

    except Exception as e:
        logger.error(f"Error generating feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate feedback")


@app.get("/api/practice/attempt/{exam_id}", tags=["Practice"])
async def get_practice_attempt(
    exam_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Load saved answers and feedback list for this exam (or empty defaults)."""
    try:
        # Get practice attempt
        result = await db.execute(
            select(PracticeAttempt).where(
                PracticeAttempt.user_id == user.id,
                PracticeAttempt.generated_exam_id == exam_id
            )
        )
        attempt = result.scalar_one_or_none()

        if not attempt:
            return {"answers": {}, "feedback": []}

        # Get feedback entries
        result = await db.execute(
            select(Feedback).where(Feedback.practice_attempt_id == attempt.id)
        )
        feedback_entries = result.scalars().all()

        feedback_data = []
        for f in feedback_entries:
            feedback_data.append({
                "question_index": f.question_index,
                "feedback_text": f.feedback_text,
                "video_url": f.video_url,
                "video_status": f.video_status,
                "created_at": f.created_at.isoformat()
            })

        return {
            "answers": json.loads(attempt.answers) if attempt.answers else {},
            "feedback": feedback_data,
            "started_at": attempt.started_at.isoformat(),
            "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None
        }

    except Exception as e:
        logger.error(f"Error retrieving practice attempt: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve practice attempt")


@app.post("/api/ai/generate_feedback", tags=["Feedback"])
async def generate_feedback_ai(
    content: FeedbackRequest,
    user: User = Depends(get_current_user),
):
    """Stateless feedback from raw question/answer; optional D-ID bundle when configured."""
    logger.info(
        "Generating feedback (ai route): user_id=%s level=%s use_video=%s",
        user.id,
        content.level,
        content.use_video,
    )
    
    try:
        config = AppConfig(
            model=ModelConfig(model_name=CHATGPT_MODEL, base_url=None),
            generation=None,
            data=DataConfig(
                question=content.question,
                answer=content.answer,
                level=content.level
            )
        )
        
        use_video = (
            content.use_video
            and bool(DID_API_KEY)
            and DID_AVATAR_ENABLED
            and not did_avatar_permission_denied()
        )
        if use_video:
            generator = FeedbackGenerator(config, use_video=True)
            result = generator.generate_feedback_with_video()
            return {
                "feedback": result["feedback_text"],
                "video_url": result.get("video_url"),
                "talk_id": result.get("talk_id"),
                "video_status": result.get("video_status"),
                "has_video": bool(result.get("video_url")),
            }

        generator = FeedbackGenerator(config, use_video=False)
        feedback = generator.generate_feedback()

        # In this branch, video was not produced: either not requested or gated off (no key / avatar off / prior 403).
        video_status_ai = "skipped" if content.use_video else "not_used"

        return {
            "feedback": feedback,
            "video_url": None,
            "talk_id": None,
            "video_status": video_status_ai,
            "has_video": False,
        }

    except ValueError:
        logger.warning("Validation error on /api/ai/generate_feedback")
        raise HTTPException(status_code=400, detail="Invalid request")
    except Exception:
        logger.exception("Error generating feedback (ai route)")
        raise HTTPException(status_code=500, detail="Failed to generate feedback")


@app.get("/api/d-id/video-status/{talk_id}", tags=["D-ID"])
async def get_video_status(
    talk_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Proxied D-ID Talk job status: GET /talks/{id} (polling). Caller must own the talk_id."""
    if not DID_API_KEY:
        raise HTTPException(status_code=503, detail="D-ID not configured")
    own = await db.execute(
        select(Feedback)
        .join(PracticeAttempt, Feedback.practice_attempt_id == PracticeAttempt.id)
        .where(
            Feedback.d_id_talk_id == talk_id,
            PracticeAttempt.user_id == user.id,
        )
    )
    if own.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Video job not found")
    try:
        video_gen = VideoGenerator()
        return video_gen.get_video_status(talk_id)
    except Exception:
        logger.exception("D-ID video status error")
        raise HTTPException(status_code=502, detail="Failed to fetch video status")


# Run the app

if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)