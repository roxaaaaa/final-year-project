import os
from typing import Optional, Literal, List

from dotenv import load_dotenv
import ollama
import json
from openai import Client, OpenAI
import logging
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


HIGHER_EXAMPLE_QUESTIONS = """
            Q: "Give three reasons for the practice of thinning forest trees.",
            Q: "Explain why strict controls are necessary when applying pesticides to farm crops.",
            Q: "Mention three factors that contribute to the formation of a gley soil."
        """
ORDINARY_EXAMPLE_QUESTIONS = """
        Q: Define the term biological control.
        Q: Crop rotation is a common practice on Irish tillage farms. Explain the underlined term. State two advantages of crop rotation.
        Q: Suggest three ways in which farmers can control / prevent liver fluke on their farm."""

# The "Persona" remains constant
SYSTEM_PROMPT = "You are a Leaving Cert Agricultural Science examiner. You provide expert, concise, and syllabus-aligned content."

# Format instructions used in the user prompt to guide JSON output
JSON_STRUCTURE_PROMPT = "Output ONLY a JSON object. Do not include any conversational text or reasoning."

@dataclass
class ModelConfig:
    model_name: str = os.getenv("MODEL_NAME", "llama3.1:8b")
    base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")

@dataclass
class GenerationConfig:
    temperature: float = 0.4
    max_tokens: int = 50
    num_questions: int = 3

@dataclass
class QuestionTaskConfig:
    topic: str = "general knowledge"
    level: Literal["higher", "ordinary"] = "higher"

@dataclass
class AppConfig:
    model: ModelConfig
    generation: GenerationConfig
    task: QuestionTaskConfig


class Generator:
    #This parameter can be either a GenerationConfig object OR None
    def __init__(self, config: Optional[AppConfig] = None):
        """
        Initialize the QuestionGenerator with the given configuration.
        Args:
            config (GenerationConfig): Configuration for question generation.
        """
        self.config = config or AppConfig(model=ModelConfig(), generation=GenerationConfig(), task=QuestionTaskConfig())
        self.client = Client(base_url=self.config.model.base_url, api_key=os.getenv("AI_API_KEY", "blablabla"))  # No API key needed for local Ollama


    def _get_ai_response(self, user_content: str) -> dict:
        """Internal helper to handle the API call logic"""
        try:
            response = self.client.chat.completions.create(
                model=self.config.model.model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"{user_content}\n\n{JSON_STRUCTURE_PROMPT}"}
                ],
                response_format={"type": "json_object"},
                temperature=self.config.generation.temperature,
            )
            content = response.choices[0].message.content
            if content is None:
                return {}
            return json.loads(content)
        except Exception as e:
            logger.error(f"AI Error: {e}")
            return {}

    def generate_questions(self, num_questions: Optional[int] = None) -> str:
        """
        Generate agricultural science exam questions
        
        Args:
            num_questions: Number of questions to generate
            
        Returns:
            List of generated questions
        """
        prompt = f"""Generate {num_questions} {self.config.task.level} level exam questions 
        on the topic of {self.config.task.topic} for level {self.config.task.level}.
        Examples: {HIGHER_EXAMPLE_QUESTIONS if self.config.task.level == "higher" else ORDINARY_EXAMPLE_QUESTIONS}
        Return as: {{"questions": ["string", "string"]}}"""
        
        data = self._get_ai_response(prompt)
        return data.get("questions", [])
    
    def generate_feedback(self, question: str, student_answer: str) -> dict:
        """
        Generate feedback for a given question.
        
        Args:
            question: The question to generate feedback
            answer: The student's answer to the question

        Returns:
            Feedback on the student's answer
        """

        prompt = f"""Review this {self.config.task.level} level answer.
        Question: {question}
        Student Answer: {student_answer}
        
        Provide feedback on accuracy and syllabus alignment.
        Return as: {{"score": "X/10", "feedback": "string"}}"""
        #, "corrections": ["string"]
        return self._get_ai_response(prompt)