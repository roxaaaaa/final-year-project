import os
import base64
from typing import Optional, Literal, List
import time
import requests

from dotenv import load_dotenv
import json
from openai import Client, OpenAI
import logging
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Environment Configuration
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.1:8b")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHAGPT_MODEL = os.getenv("CHAGPT_MODEL", "gpt-4o-mini")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")

# D-ID Configuration
DID_API_KEY = os.getenv("DID_API_KEY")
DID_BASE_URL = "https://api.d-id.com"
DID_PRESENTER_ID = os.getenv("DID_PRESENTER_ID", "v2_public_Amber@0zSz8kflCN")  # Default: Amber
DID_CLIPS_ENABLED = os.getenv("DID_CLIPS_ENABLED", "true").strip().lower() in ("1", "true", "yes")
_DID_CLIPS_PERMISSION_DENIED = False


class DIDClipsPermissionDenied(Exception):
    """D-ID account/key cannot create Clips (HTTP 403 clips:write)."""


def _did_clips_permission_denied(status_code: int, body: str) -> bool:
    if status_code != 403:
        return False
    b = (body or "").lower()
    return "permission" in b or "clips:write" in b


def did_clips_write_permission_denied() -> bool:
    """True after D-ID returned 403 clips:write in this process (read each call; do not cache the bool)."""
    return _DID_CLIPS_PERMISSION_DENIED


if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables!")

HIGHER_EXAMPLE_QUESTIONS = """
Higher level questions requires in-depth understanding, precise definitions, and detailed scientific methods for experiments, along with higher-order analysis of environmental topics. 
            {"question": "Give three reasons for the practice of thinning forest trees."},
            {"question": "Explain why strict controls are necessary when applying pesticides to farm crops."},
            {"question": "Mention three factors that contribute to the formation of a gley soil."}
        """

ORDINARY_EXAMPLE_QUESTIONS = """
Ordinary level question requires a solid understanding of fundamental agricultural practices, terminology, and key experiments
        {"question": "Define the term biological control."}
        {"question": "Crop rotation is a common practice on Irish tillage farms. Explain the underlined term. State two advantages of crop rotation"}.
        {"question": "Suggest three ways in which farmers can control / prevent liver fluke on their farm."}"""

SYSTEM_PROMPT = """You are a Leaving Cert Agricultural Science examiner. You provide expert, concise, and syllabus-aligned content."""

JSON_STRUCTURE_PROMPT = "Output ONLY a JSON object. Do not include any conversational text or reasoning."

@dataclass
class ModelConfig:
    model_name: str 
    api_key: str = OPENAI_API_KEY
    base_url: Optional[str] = OLLAMA_BASE_URL

@dataclass
class GenerationConfig:
    temperature: float = 0.4
    max_tokens: int = 250
    num_questions: int = 3

@dataclass
class DataConfig:
    level: Literal["higher", "ordinary"] = "ordinary"
    topic: Optional[str] = "general knowledge"
    question: Optional[str] = ""
    answer: Optional[str] = ""

@dataclass
class AppConfig:
    model: ModelConfig
    data: DataConfig
    generation: Optional[GenerationConfig]

class VideoGenerator:
    """
    Handles video generation using D-ID's Clips API.
    Documentation: https://docs.d-id.com/docs/v3-pro-avatar-quickstart.md
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = DID_BASE_URL):
        """Initialize D-ID client with API credentials."""
        key = api_key or DID_API_KEY
        if not key:
            raise ValueError("DID_API_KEY not found in environment variables!")
        
        self.api_key = key
        self.base_url = base_url
        # base64(user:password); env is often already "user:secret" — avoid an extra trailing ":".
        credential = key if ":" in key else f"{key}:"
        token = base64.b64encode(credential.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }
    
    def create_video(self, script: str, presenter_id: str = DID_PRESENTER_ID) -> str:
        """
        Create a video with D-ID avatar speaking the feedback.
        
        Args:
            script: The text the avatar should speak
            presenter_id: ID of the avatar presenter (default: Amber)
        
        Returns:
            clip_id: The ID of the created video clip
        """
        try:
            payload = {
                "presenter_id": presenter_id,
                "script": {
                    "type": "text",
                    "input": script
                }
            }
            
            response = requests.post(
                f"{self.base_url}/clips",
                headers=self.headers,
                json=payload,
                timeout=60,
            )
            global _DID_CLIPS_PERMISSION_DENIED
            if response.status_code not in (200, 201):
                if _did_clips_permission_denied(response.status_code, response.text):
                    _DID_CLIPS_PERMISSION_DENIED = True
                    logger.warning(
                        "D-ID returned 403: this API key cannot use Clips (clips:write). "
                        "Set DID_CLIPS_ENABLED=false to avoid retries, or use a D-ID plan with Clips access. Body: %s",
                        (response.text or "")[:500],
                    )
                    raise DIDClipsPermissionDenied(response.text)
                logger.error(f"D-ID Video Creation Error: {response.text}")
                raise Exception(f"Failed to create video: {response.text}")
            
            data = response.json()
            clip_id = data.get("id")
            logger.info(f"Video created with ID: {clip_id}")
            return clip_id

        except DIDClipsPermissionDenied:
            raise
        except Exception as e:
            logger.error(f"D-ID Video Creation Error: {e}")
            raise
    
    def get_video_status(self, clip_id: str) -> dict:
        """
        Check the status of a video clip.
        
        Args:
            clip_id: The ID of the video clip
        
        Returns:
            dict: Status information including result_url when ready
        """
        try:
            response = requests.get(
                f"{self.base_url}/clips/{clip_id}",
                headers=self.headers
            )
            
            if response.status_code != 200:
                logger.error(f"D-ID Status Check Error: {response.text}")
                raise Exception(f"Failed to get status: {response.text}")
            
            return response.json()
            
        except Exception as e:
            logger.error(f"D-ID Status Check Error: {e}")
            raise
    
    def wait_for_video(self, clip_id: str, max_wait: int = 60, poll_interval: int = 2) -> Optional[str]:
        """
        Poll the API until video is ready and return the result URL.
        
        Args:
            clip_id: The ID of the video clip
            max_wait: Maximum seconds to wait
            poll_interval: Seconds between polls
        
        Returns:
            result_url: URL to the completed video, or None if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                status = self.get_video_status(clip_id)
                
                if status.get("status") == "done":
                    result_url = status.get("result_url")
                    logger.info(f"Video ready: {result_url}")
                    return result_url
                elif status.get("status") == "error":
                    logger.error(f"Video generation failed: {status.get('error')}")
                    return None
                
                logger.info(f"Video status: {status.get('status')} - waiting...")
                time.sleep(poll_interval)
                
            except Exception as e:
                logger.error(f"Error checking video status: {e}")
                time.sleep(poll_interval)
        
        logger.warning(f"Video generation timeout after {max_wait}s")
        return None
    
    def get_presenters(self) -> List[dict]:
        """Get list of available presenters."""
        try:
            response = requests.get(
                f"{self.base_url}/clips/presenters",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get presenters: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching presenters: {e}")
            return []


class QuestionGenerator:
    """Generates exam questions using local Ollama or OpenAI."""
    
    def __init__(self, config: Optional[AppConfig] = None):
        """Initialize the QuestionGenerator with the given configuration."""
        if config is None:
            self.config = AppConfig(
                model=ModelConfig(model_name=MODEL_NAME, api_key=""), 
                generation=GenerationConfig(),
                data=DataConfig()
            )
        else:
            self.config = config
        
        self.client = Client(base_url=self.config.model.base_url)

    def generate_questions(self) -> List[str]:
        """
        Generate agricultural science exam questions.
        
        Returns:
            List of generated questions
        """
        prompt = f"""Generate exam questions 
        on the topic of {self.config.data.topic} for level {self.config.data.level}.
        Examples: {HIGHER_EXAMPLE_QUESTIONS if self.config.data.level == "higher" else ORDINARY_EXAMPLE_QUESTIONS}
        Return a json structured response {{"question": "string"}}"""
        questions = []

        if self.config.generation is None:
            self.config.generation = GenerationConfig()

        for _ in range(self.config.generation.num_questions):
            try:
                response = self.client.chat.completions.create(
                    model=self.config.model.model_name,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"{prompt}\n\n{JSON_STRUCTURE_PROMPT}"}
                    ],
                    response_format={"type": "json_object"},
                    temperature=self.config.generation.temperature,
                    max_tokens=self.config.generation.max_tokens,
                )
                content = response.choices[0].message.content
                if content:
                    data = json.loads(content)
                    question_text = data.get("question")
                    if question_text:
                        questions.append(question_text)
                        print(f"Generated question: {question_text}")
                    else:
                        logger.error("Question does not exist in response")
            except Exception as e:
                logger.error(f"AI Error: {e}")
        
        return questions


class FeedbackGenerator:
    """
    Generates feedback using ChatGPT and optionally creates D-ID avatar videos.
    """
    
    def __init__(self, config: Optional[AppConfig] = None, use_video: bool = True):
        """
        Initialize the FeedbackGenerator.
        
        Args:
            config: AppConfig object with model and data settings
            use_video: Whether to generate D-ID avatar videos (default: True)
        """
        if config is None:
            self.config = AppConfig(
                model=ModelConfig(model_name=CHAGPT_MODEL, base_url=None), 
                generation=None,
                data=DataConfig()
            )
        else:
            self.config = config
        
        self.client = OpenAI(api_key=self.config.model.api_key or OPENAI_API_KEY)
        self.use_video = use_video
        if use_video and DID_API_KEY and DID_CLIPS_ENABLED and not _DID_CLIPS_PERMISSION_DENIED:
            self.video_generator = VideoGenerator()
        else:
            self.video_generator = None

    def generate_feedback(self) -> str:
        """
        Generate teacher feedback for a student answer.
        
        Returns:
            Feedback text from the teacher
        """
        user_content = f"""
        You are tutoring a student right now. 
        Question: {self.config.data.question}
        Student Answer: {self.config.data.answer}
        Level: {self.config.data.level}
        
        Provide feedback (as a teacher talking to a student) on accuracy and syllabus alignment. Give feedback:
        - If there is anything incorrect in the answer, if yes what
        - How to improve 

        Keep it concise (2-3 sentences max). No suggestions at the end, all text must be the same font, no emojis.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.model.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a strict but helpful Agricultural Science teacher and Leaving Certificate examiner."
                    },
                    {"role": "user", "content": user_content}
                ],
                temperature=0.7,
                max_tokens=60
            )
            
            feedback_text = response.choices[0].message.content or ""
            print(f"Generated feedback: {feedback_text}")
            return feedback_text
            
        except Exception as e:
            logger.error(f"Feedback Generation Error: {e}")
            return "Error generating feedback. Please try again."

    def generate_feedback_with_video(self) -> dict:
        """
        Generate feedback and create a D-ID avatar video of the feedback.
        
        Returns:
            dict with keys:
                - feedback_text: The generated feedback
                - video_url: URL to the D-ID avatar video (or None if failed)
                - clip_id: D-ID clip ID for reference
        """
        # First generate the feedback text
        feedback_text = self.generate_feedback()
        
        result = {
            "feedback_text": feedback_text,
            "video_url": None,
            "clip_id": None,
            "video_status": "not_used",
        }

        if not self.use_video or not DID_API_KEY:
            result["video_status"] = "skipped"
            logger.info("Video generation skipped (disabled or no API key)")
            return result
        if not DID_CLIPS_ENABLED:
            result["video_status"] = "skipped"
            logger.info("D-ID Clips skipped (DID_CLIPS_ENABLED=false)")
            return result
        if _DID_CLIPS_PERMISSION_DENIED or self.video_generator is None:
            result["video_status"] = "skipped"
            logger.info("D-ID Clips skipped (no generator or prior clips:write denial)")
            return result

        try:
            # Create D-ID video with the feedback text
            logger.info("Creating D-ID avatar video...")
            clip_id = self.video_generator.create_video(feedback_text)
            result["clip_id"] = clip_id
            
            # Wait for video to be ready
            logger.info(f"Waiting for video {clip_id} to render...")
            video_url = self.video_generator.wait_for_video(clip_id, max_wait=60)
            result["video_url"] = video_url
            result["video_status"] = "completed" if video_url else "failed"
            
            if video_url:
                logger.info(f"Video ready: {video_url}")
            else:
                logger.warning("Video creation timed out or failed")
            
        except DIDClipsPermissionDenied:
            result["video_status"] = "skipped"
            logger.info("Returning feedback text without video (Clips permission denied)")
        except Exception as e:
            logger.error(f"Video generation error: {e}")
            result["video_status"] = "failed"
            logger.info("Returning feedback text without video")
        
        return result


# if __name__ == "__main__":
    # Example: Generate questions
    # config = AppConfig(
    #     model=ModelConfig(model_name=MODEL_NAME, api_key="ollama"),
    #     data=DataConfig(level="ordinary", topic="soil formation"),
    #     generation=GenerationConfig()
    # ) 
    # generator = QuestionGenerator(config)
    # print("Generating questions...")
    # print(generator.generate_questions())

    # Example: Generate feedback with video
    # sample_data = DataConfig(
    #     question="Explain why strict controls are necessary when applying pesticides to farm crops.",
    #     answer="To prevent them from getting into the water and killing bees."
    # )
    # config1 = AppConfig(
    #     model=ModelConfig(model_name=CHAGPT_MODEL, base_url=""),
    #     generation=None,
    #     data=sample_data
    # )
    # generator = FeedbackGenerator(config1, use_video=True)
    # print("Generating feedback with video...")
    # result = generator.generate_feedback_with_video()
    # print(f"Feedback: {result['feedback_text']}")
    # print(f"Video URL: {result['video_url']}")
