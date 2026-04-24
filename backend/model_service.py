"""LLM calls for exam questions and feedback, plus optional D-ID talking-head video."""

import os
import time
import base64
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Literal, List, Any

import httpx
from dotenv import load_dotenv
import json
from openai import OpenAI
import ollama
import logging
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


def _model_uses_max_completion_tokens(model: str) -> bool:
    """Newer / reasoning-style chat models reject `max_tokens` and use `max_completion_tokens`."""
    m = (model or "").lower()
    if m.startswith(("o1", "o3", "o4")):
        return True
    if "gpt-5" in m:
        return True
    return False


def _openai_chat_completion(
    client: OpenAI,
    *,
    model: str,
    messages: list,
    temperature: Optional[float],
    max_output_tokens: int,
    response_format: Optional[dict] = None,
):
    """
    Route `max_tokens` vs `max_completion_tokens` by model. Reasoning models also need a
    large enough completion budget or `message.content` can be empty (tokens used internally).
    """
    kw: dict = {"model": model, "messages": messages}
    if temperature is not None:
        kw["temperature"] = temperature
    if response_format is not None:
        kw["response_format"] = response_format
    if _model_uses_max_completion_tokens(model):
        return client.chat.completions.create(**kw, max_completion_tokens=max_output_tokens)
    try:
        return client.chat.completions.create(**kw, max_tokens=max_output_tokens)
    except Exception as e:
        err = str(e).lower()
        if "max_completion_tokens" in err and "max_tokens" in err:
            return client.chat.completions.create(**kw, max_completion_tokens=max_output_tokens)
        raise

# Default model and API keys (see .env)
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.1:8b")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHATGPT_MODEL = os.getenv("CHATGPT_MODEL", "gpt-4o-mini")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")

# D-ID Configuration (Talks API only: POST /talks)
DID_API_KEY = os.getenv("DID_API_KEY") or None
DID_BASE_URL = os.getenv("DID_BASE_URL", "https://api.d-id.com").rstrip("/")
# Master switch for D-ID avatar video. DID_CLIPS_ENABLED is still read as a legacy alias.
_did_avatar_raw = os.getenv("DID_AVATAR_ENABLED")
if _did_avatar_raw is None:
    _did_avatar_raw = os.getenv("DID_CLIPS_ENABLED", "true")
DID_AVATAR_ENABLED = _did_avatar_raw.strip().lower() in ("1", "true", "yes")
# Frontal face photo (HTTPS .jpg/.png). Default: D-ID hosted presenter (reliable for Talks; instructor-style male).
# Official quickstart uses Noelle_f; override with DID_TALK_SOURCE_URL if you want another D-ID presenter image.
_DEFAULT_DID_TALK_SOURCE_URL = (
    "https://create-images-results.d-id.com/DefaultPresenters/William_m/image.png"
)
DID_TALK_SOURCE_URL = (
    os.getenv("DID_TALK_SOURCE_URL", _DEFAULT_DID_TALK_SOURCE_URL) or _DEFAULT_DID_TALK_SOURCE_URL
).strip()
# Microsoft Azure Neural voice for Talks TTS (see GET https://api.d-id.com/voices). en-IE-ConnorNeural = male English (Ireland).
DID_TALK_VOICE_ID = os.getenv("DID_TALK_VOICE_ID", "en-IE-ConnorNeural").strip()
# After a 403 on D-ID avatar creation, skip further video POSTs until process restart.
_DID_AVATAR_PERMISSION_DENIED = False


class DIDAvatarPermissionDenied(RuntimeError):
    """Raised when the D-ID API key cannot create a Talk (e.g. talks:write permission)."""


def _did_talk_permission_denied(status_code: int, body: str) -> bool:
    """True if D-ID said 403 and the body looks like a Talks permission error."""
    if status_code != 403:
        return False
    b = (body or "").lower()
    return "permission" in b or "talks:write" in b


def did_avatar_permission_denied() -> bool:
    """True after D-ID returned 403 for Talks creation; read on each call."""
    return _DID_AVATAR_PERMISSION_DENIED


if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables!")

HIGHER_EXAMPLE_QUESTIONS = """
Higher level questions require in-depth understanding, precise definitions, and detailed scientific methods for experiments, along with higher-order analysis of environmental topics.
            {"question": "Give three reasons for the practice of thinning forest trees."},
            {"question": "Explain why strict controls are necessary when applying pesticides to farm crops."},
            {"question": "Mention three factors that contribute to the formation of a gley soil."}
        """

ORDINARY_EXAMPLE_QUESTIONS = """
Ordinary level tests clear recall and short explanations — one main idea per stem, wording similar to past papers (not mini essays).
Format examples only (do not copy topics or phrasing):
        {"question": "Define the term biological control."}
        {"question": "State two ways in which good grassland management can benefit the dairy farmer."}
        {"question": "What is meant by the term carrying capacity when referring to livestock?"}
        {"question": "Give one advantage and one disadvantage of monoculture in tillage farming."}
        {"question": "Explain how overstocking of grazing land can damage soil structure."}"""

# Used when several questions are requested in parallel (same topic); reduces mode-collapse on one template (e.g. biosecurity repeated).
ORDINARY_BATCH_ANGLE_HINTS = (
    "Angle: soil, drainage, soil structure, pH, or plant nutrition — pick one focus that fits the topic.",
    "Angle: crop production, rotation, cultivation, or tillage management — pick one focus that fits the topic.",
    "Angle: grassland, grazing, silage, or fodder conservation — pick one focus that fits the topic.",
    "Angle: animal housing, feeding, milk/meat production, or welfare — pick one focus that fits the topic.",
    "Angle: parasites, vaccination, or herd health — pick one specific idea; avoid repeating a generic biosecurity definition stem.",
    "Angle: breeding, genetics, anatomy, or physiology of a named farm species — pick one focus that fits the topic.",
    "Angle: environment, forestry, pollution, or sustainable farm practice — pick one focus that fits the topic.",
)

SYSTEM_PROMPT = """You are a Leaving Cert Agricultural Science examiner.

When generating exam questions you output only the question as it would appear on the paper: a single stem (the wording students see). Do not add marking guidance, rubrics, or hints about what the answer must contain.

Forbidden in the question text: phrases like "In your answer", "Your answer should", "define X and state Y", bullet or numbered lists of tasks, or step-by-step instructions (e.g. demanding controls, measurements, or experimental write-ups inside the question). Do not pack multiple disconnected tasks into one question.

Allowed: short context if needed, then one clear command (e.g. Explain / Describe / Outline / Account for / Suggest) matching real exam style and the requested level.

Ordinary level: keep stems short (often one sentence). Test one concept only. Vary command words and scenarios; do not lean on the same template repeatedly (e.g. several stems that all ask to define or explain one generic farm term with only small wording changes).

Factual discipline: stay within standard Leaving Cert Agricultural Science content. Do not invent statistics, legal citations, Department scheme names, or branded products as if they were exam facts. Use generic Irish farm context where helpful, without made-up place names or survey results."""

JSON_STRUCTURE_PROMPT = (
    'Output ONLY a single JSON object with this exact shape: {"question": "<exam question text>"}. '
    "The value must be the question stem only (no preamble). "
    "Escape double quotes inside the question as \\\". No markdown fences, no commentary."
)


def _strip_markdown_json_fence(text: str) -> str:
    """Remove ```json ... ``` wrappers if the model added them."""
    t = text.strip()
    if not t.startswith("```"):
        return t
    lines = t.split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    while lines and lines[-1].strip().startswith("```"):
        lines.pop()
    return "\n".join(lines).strip()


def _extract_balanced_json_object(text: str) -> Optional[str]:
    """Return the first top-level {...} span, respecting string literals."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    return None


def _parse_question_json_from_content(raw: str) -> Optional[str]:
    """Parse model output into a single question string."""
    if not raw or not raw.strip():
        return None
    stripped = _strip_markdown_json_fence(raw)
    blob = _extract_balanced_json_object(stripped)
    if blob is None:
        blob = stripped
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return None
    q = data.get("question")
    if isinstance(q, str) and q.strip():
        return q.strip()
    return None


@dataclass
class ModelConfig:
    """Which model to call; optional Ollama base URL."""
    model_name: str
    api_key: str = OPENAI_API_KEY
    base_url: Optional[str] = OLLAMA_BASE_URL

@dataclass
class GenerationConfig:
    """Sampling and how many questions to ask for in one run."""
    temperature: float = 0.4
    # Reasoning-style models can consume most of a small budget before visible JSON; keep this comfortably high.
    max_tokens: int = 1200
    num_questions: int = 3

@dataclass
class DataConfig:
    """Exam level, topic, and optional Q/A for feedback."""
    level: Literal["higher", "ordinary"] = "ordinary"
    topic: Optional[str] = "general knowledge"
    question: Optional[str] = ""
    answer: Optional[str] = ""

@dataclass
class AppConfig:
    """Bundle passed into question or feedback generators."""
    model: ModelConfig
    data: DataConfig
    generation: Optional[GenerationConfig]

def _did_auth_headers(api_key: str) -> dict:
    """D-ID Basic auth: base64(username:password). Keys are often already user:secret — avoid a trailing ':'."""
    credential = api_key if ":" in api_key else f"{api_key}:"
    token = base64.b64encode(credential.encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


class VideoGenerator:
    """D-ID talking-head video via POST /talks (photo avatar + TTS)."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        key = api_key or DID_API_KEY
        if not key:
            raise ValueError("DID_API_KEY not found in environment variables!")
        self.api_key = key
        self.base_url = (base_url or DID_BASE_URL).rstrip("/")
        self.headers = _did_auth_headers(self.api_key)
        self._talk_source_url = DID_TALK_SOURCE_URL
        self._talk_voice_id = DID_TALK_VOICE_ID

    def _raise_or_set_denied(self, r: httpx.Response, *, api_label: str) -> None:
        """On 403 permission errors, set a flag so later calls skip D-ID."""
        global _DID_AVATAR_PERMISSION_DENIED
        if _did_talk_permission_denied(r.status_code, r.text):
            _DID_AVATAR_PERMISSION_DENIED = True
            logger.warning(
                "D-ID returned 403 for %s. Set DID_AVATAR_ENABLED=false to disable avatar video, "
                "or fix D-ID key permissions. Body: %s",
                api_label,
                r.text,
            )
            raise DIDAvatarPermissionDenied(r.text)
        logger.error("D-ID %s creation error (%s): %s", api_label, r.status_code, r.text)
        raise RuntimeError(f"Failed to create video: {r.text}")

    def _create_talk(self, script: str) -> str:
        """POST /talks; return new talk id."""
        text = (script or "").strip()
        if len(text) < 3:
            text = "Feedback."
        script_body: dict[str, Any] = {"type": "text", "input": text}
        if self._talk_voice_id:
            script_body["provider"] = {
                "type": "microsoft",
                "voice_id": self._talk_voice_id,
            }
        payload: dict[str, Any] = {
            "source_url": self._talk_source_url,
            "script": script_body,
        }
        with httpx.Client(timeout=60.0) as client:
            r = client.post(f"{self.base_url}/talks", headers=self.headers, json=payload)
        if r.status_code not in (200, 201):
            self._raise_or_set_denied(r, api_label="Talks")
        data = r.json()
        talk_id = data.get("id")
        logger.info("D-ID Talk created with id: %s", talk_id)
        return talk_id

    def create_talk(self, script: str) -> str:
        """Create a D-ID Talk; returns talk job id."""
        return self._create_talk(script)

    def get_video_status(self, job_id: str) -> dict[str, Any]:
        """GET /talks/{id} — status and result_url when done."""
        path = f"{self.base_url}/talks/{job_id}"
        with httpx.Client(timeout=30.0) as client:
            r = client.get(path, headers=self.headers)
        if r.status_code not in (200, 201):
            logger.error("D-ID status error (%s): %s", r.status_code, r.text)
            raise RuntimeError(f"Failed to get status: {r.text}")
        return r.json()

    def wait_for_video(self, job_id: str, max_wait: int = 60, poll_interval: int = 2) -> Optional[str]:
        """Poll until done, error, or timeout; return video URL or None."""
        start = time.time()
        while time.time() - start < max_wait:
            try:
                status = self.get_video_status(job_id)
                st = status.get("status")
                if st == "done":
                    result_url = status.get("result_url")
                    logger.info("Video ready: %s", result_url)
                    return result_url
                if st in ("error", "rejected"):
                    logger.error("Video generation failed: %s", status.get("error"))
                    return None
                logger.info("Video status: %s - waiting...", st)
            except Exception as e:
                logger.error("Error checking video status: %s", e)
            time.sleep(poll_interval)
        logger.warning("Video generation timeout after %ss", max_wait)
        return None


class QuestionGenerator:
    """Generates exam questions using local Ollama or OpenAI."""
    
    def __init__(self, config: Optional[AppConfig] = None):
        """Build clients: Ollama if base_url is set, otherwise OpenAI."""
        if config is None:
            self.config = AppConfig(
                model=ModelConfig(model_name=MODEL_NAME, api_key=""), 
                generation=GenerationConfig(),
                data=DataConfig()
            )
        else:
            self.config = config

        self._openai_model_name: Optional[str] = None
        # Local Ollama when base_url is set (strip /v1 for the ollama SDK host).
        if self.config.model.base_url:
            self.use_ollama = True
            # Extract host from base_url (e.g., http://localhost:11434/v1 -> http://localhost:11434)
            base_url = self.config.model.base_url.replace("/v1", "")
            self.ollama_client = ollama.Client(host=base_url)
            self.openai_client: Optional[OpenAI] = None
        else:
            self.use_ollama = False
            self.openai_client = OpenAI(api_key=OPENAI_API_KEY)

    def _fallback_to_openai(self) -> None:
        """Switch to OpenAI after Ollama errors (e.g. daemon not running). Uses CHATGPT_MODEL, not Ollama model ids."""
        if not OPENAI_API_KEY:
            raise RuntimeError("Ollama failed and OPENAI_API_KEY is missing; cannot fall back.")
        logger.warning(
            "Ollama unavailable; falling back to OpenAI model %s",
            CHATGPT_MODEL,
        )
        self.use_ollama = False
        self._openai_model_name = CHATGPT_MODEL
        if self.openai_client is None:
            self.openai_client = OpenAI(api_key=OPENAI_API_KEY)

    def _complete_openai_and_parse(self, messages: list) -> Optional[str]:
        """Single OpenAI chat completion and JSON parse. Safe for parallel calls when `use_ollama` is False."""
        assert self.openai_client is not None
        openai_model = self._openai_model_name or self.config.model.model_name
        assert self.config.generation is not None
        json_mode: Optional[dict] = {"type": "json_object"}
        try:
            response = _openai_chat_completion(
                self.openai_client,
                model=openai_model,
                messages=messages,
                temperature=self.config.generation.temperature,
                max_output_tokens=self.config.generation.max_tokens,
                response_format=json_mode,
            )
        except Exception as api_err:
            err_s = str(api_err).lower()
            if "response_format" in err_s or "json_object" in err_s:
                logger.warning(
                    "JSON response_format not supported for %s (%s); retrying without it.",
                    openai_model,
                    api_err,
                )
                response = _openai_chat_completion(
                    self.openai_client,
                    model=openai_model,
                    messages=messages,
                    temperature=self.config.generation.temperature,
                    max_output_tokens=self.config.generation.max_tokens,
                    response_format=None,
                )
            else:
                raise
        content = (response.choices[0].message.content or "") if response.choices else ""
        if not content:
            return None
        question_text = _parse_question_json_from_content(content)
        if question_text:
            return question_text
        logger.error(
            "Could not parse question JSON from model output (first 200 chars): %r",
            content[:200],
        )
        return None

    def _messages_for_question(self, batch_index: int, batch_total: int) -> list:
        """System + user messages for one stem; ordinary-level parallel runs get rotated angle hints."""
        topic = self.config.data.topic or "general knowledge"
        level = self.config.data.level
        examples = HIGHER_EXAMPLE_QUESTIONS if level == "higher" else ORDINARY_EXAMPLE_QUESTIONS
        user_lines = [
            f"Generate one exam question on the topic of {topic} for level {level}.",
            "Tone and length: match a real Leaving Cert short-answer stem — usually one or two sentences, no checklist of sub-parts.",
            f"Style examples (format only; do not copy wording): {examples}",
        ]
        if level == "ordinary" and batch_total > 1:
            hint = ORDINARY_BATCH_ANGLE_HINTS[batch_index % len(ORDINARY_BATCH_ANGLE_HINTS)]
            user_lines.append(
                f"This is item {batch_index + 1} of {batch_total} generated together on the same topic. "
                f"{hint} The stem must not duplicate the same central term or task pattern as the other items would."
            )
        user_lines.append(f'Return a json structured response {{"question": "string"}}')
        user_content = "\n\n".join(user_lines) + f"\n\n{JSON_STRUCTURE_PROMPT}"
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

    def generate_questions(self) -> List[str]:
        """Return up to num_questions stems (JSON parsed); OpenAI calls run in parallel."""
        questions: List[str] = []

        if self.config.generation is None:
            self.config.generation = GenerationConfig()

        n = self.config.generation.num_questions

        # OpenAI-only: concurrent requests (independent stems per call).
        if not self.use_ollama:
            max_workers = min(max(n, 1), 8)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(
                        self._complete_openai_and_parse,
                        self._messages_for_question(i, n),
                    )
                    for i in range(n)
                ]
                for fut in futures:
                    try:
                        q = fut.result()
                        if q:
                            questions.append(q)
                    except Exception as e:
                        logger.error("AI Error: %s", e)
            return questions

        for i in range(n):
            messages = self._messages_for_question(i, n)
            try:
                content = ""
                if self.use_ollama:
                    try:
                        response = self.ollama_client.chat(
                            model=self.config.model.model_name,
                            messages=messages,
                            stream=False,
                        )
                        content = response.get("message", {}).get("content", "") or ""
                    except Exception as ollama_err:
                        logger.warning(
                            "Ollama request failed (%s); falling back to OpenAI.",
                            ollama_err,
                        )
                        self._fallback_to_openai()

                if not self.use_ollama:
                    q = self._complete_openai_and_parse(messages)
                    if q:
                        questions.append(q)
                elif content:
                    question_text = _parse_question_json_from_content(content)
                    if question_text:
                        questions.append(question_text)
                    else:
                        logger.error(
                            "Could not parse question JSON from model output (first 200 chars): %r",
                            content[:200],
                        )
            except Exception as e:
                logger.error("AI Error: %s", e)

        return questions


class FeedbackGenerator:
    """Generates feedback using ChatGPT; optional D-ID Talks avatar video."""
    
    def __init__(self, config: Optional[AppConfig] = None, use_video: bool = True):
        """OpenAI client for feedback; VideoGenerator only if video is on and D-ID is allowed."""
        if config is None:
            self.config = AppConfig(
                model=ModelConfig(model_name=CHATGPT_MODEL, base_url=None), 
                generation=None,
                data=DataConfig()
            )
        else:
            self.config = config

        key = self.config.model.api_key or OPENAI_API_KEY
        if not key or key == "ollama":
            key = OPENAI_API_KEY
        self.client = OpenAI(api_key=key)
        self.use_video = use_video
        if use_video and DID_API_KEY and DID_AVATAR_ENABLED and not _DID_AVATAR_PERMISSION_DENIED:
            self.video_generator = VideoGenerator()
        else:
            self.video_generator = None

    def generate_feedback(self) -> str:
        """Short teacher-style feedback for config.data.question / answer, or an error string."""
        user_content = f"""Question:
{self.config.data.question}

Student answer:
{self.config.data.answer}

Level: {self.config.data.level}

Reply as a teacher in at most three short sentences. Comment only on what the student actually wrote: whether it addresses the question, the main gap or mistake if any, and one concrete way to improve. Do not give a full model answer, marking scheme, or bullet list. Do not restate the question as a checklist of tasks (no "you must define… / outline an experiment…"). If the answer is off-topic, nonsense, or empty, say that briefly and ask them to answer the question in their own words — do not teach the entire topic."""
        
        try:
            # Short answer in prompt, but reasoning models can spend most of the budget before `content` appears.
            response = _openai_chat_completion(
                self.client,
                model=self.config.model.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a strict but helpful Leaving Certificate Agricultural Science teacher. "
                            "You write at most three short sentences of feedback. No bullet points or numbered lists. "
                            "Never output an implied marking scheme or full sample answer."
                        ),
                    },
                    {"role": "user", "content": user_content}
                ],
                temperature=0.7,
                max_output_tokens=400,
            )

            choice = response.choices[0]
            feedback_text = (choice.message.content or "").strip()
            if not feedback_text:
                fr = getattr(choice, "finish_reason", None)
                logger.warning(
                    "Empty feedback completion (model=%s finish_reason=%s)",
                    self.config.model.model_name,
                    fr,
                )
                return "Error generating feedback. Please try again."

            logger.info("Generated feedback: %s", feedback_text[:200] + ("…" if len(feedback_text) > 200 else ""))
            return feedback_text

        except Exception as e:
            logger.error(f"Feedback Generation Error: {e}")
            return "Error generating feedback. Please try again."

    def generate_feedback_with_video(self) -> dict:
        """Same as generate_feedback, plus talk_id, video_url, and video_status for the UI."""
        # Text first, then optional D-ID job.
        feedback_text = self.generate_feedback()
        
        result: dict = {
            "feedback_text": feedback_text,
            "video_url": None,
            "talk_id": None,
            "video_status": "not_used",
        }

        if not self.use_video or not self.video_generator:
            if self.use_video and not DID_AVATAR_ENABLED:
                result["video_status"] = "skipped"
                logger.info("D-ID avatar video disabled (DID_AVATAR_ENABLED=false)")
            elif self.use_video and _DID_AVATAR_PERMISSION_DENIED:
                result["video_status"] = "skipped"
                logger.info("D-ID avatar video skipped (prior 403 from D-ID for this process)")
            else:
                logger.info("Video generation skipped (disabled or no DID_API_KEY)")
            return result

        try:
            logger.info("Creating D-ID Talk (avatar video)...")
            talk_id = self.video_generator.create_talk(feedback_text)
            result["talk_id"] = talk_id
            logger.info("Waiting for video %s to render...", talk_id)
            video_url = self.video_generator.wait_for_video(talk_id, max_wait=60)
            result["video_url"] = video_url
            result["video_status"] = "completed" if video_url else "failed"
        except DIDAvatarPermissionDenied:
            result["video_status"] = "skipped"
        except Exception as e:
            logger.error("D-ID video generation failed: %s", e)
            result["video_status"] = "failed"

        return result



