import os
from typing import Optional, Literal, List

from dotenv import load_dotenv

import json
from openai import Client, OpenAI
import logging
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.1:8b")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHAGPT_MODEL = os.getenv("CHAGPT_MODEL", "gpt-5.4-nano")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
if not OPENAI_API_KEY:
    raise ValueError("KEY not found in environment variables!")

HIGHER_EXAMPLE_QUESTIONS = """
            Q: "Give three reasons for the practice of thinning forest trees.",
            Q: "Explain why strict controls are necessary when applying pesticides to farm crops.",
            Q: "Mention three factors that contribute to the formation of a gley soil."
        """
ORDINARY_EXAMPLE_QUESTIONS = """
        Q: Define the term biological control.
        Q: Crop rotation is a common practice on Irish tillage farms. Explain the underlined term. State two advantages of crop rotation.
        Q: Suggest three ways in which farmers can control / prevent liver fluke on their farm."""

SYSTEM_PROMPT = "You are a Leaving Cert Agricultural Science examiner. You provide expert, concise, and syllabus-aligned content."

# Format instructions used in the user prompt to guide JSON output
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
    level: str
    topic: Optional[str] = "general knowledge"
    question : Optional[str] = ""
    answer: Optional[str] = ""

@dataclass
class AppConfig:
    model: ModelConfig
    data: DataConfig
    generation: Optional[GenerationConfig]

class QuestionGenerator:
    #This parameter can be either a AppConfig object OR None
    def __init__(self, config: Optional[AppConfig] = None):
        """
        Initialize the QuestionGenerator with the given configuration.
        """
        if config is None:
            self.config = config or AppConfig(
                model=ModelConfig(model_name=MODEL_NAME, api_key=""), 
                generation=GenerationConfig(),
                data=DataConfig(level=""))
        else:
            self.config = config
        self.client = Client(base_url=self.config.model.base_url) 


    def generate_questions(self) -> List[str]:
        """
        Generate agricultural science exam questions
        
        Args:
            num_questions: Number of questions to generate
            
        Returns:
            List of generated questions
        """
        prompt = f"""Generate {self.config.data.level} level exam questions 
        on the topic of {self.config.data.topic} for level {self.config.data.level}.
        Examples: {HIGHER_EXAMPLE_QUESTIONS if self.config.data.level == "higher" else ORDINARY_EXAMPLE_QUESTIONS}
        Return a a json {{"question": "string"}}"""
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
                if content is not None:
                    data = json.loads(content)
                else:
                    logger.warning("nothing got generated")
                    data = {}
                questions.append(data.get("question", []))
            except Exception as e:
                logger.error(f"AI Error: {e}")
        return questions

class FeedbackGenerator:
    def __init__(self, config: Optional[AppConfig] = None):
        if config is None:
            self.config = config or AppConfig(
                model=ModelConfig(model_name=CHAGPT_MODEL, base_url = None), 
                generation=None,
                data=DataConfig(level=""))
        else:
            self.config = config
        self.client = OpenAI(api_key=self.config.model.api_key or OPENAI_API_KEY)
        

    def generate_feedback(self) -> str:
        """
        Generate feedback for a specific question and answer pair.
        """
        user_content = f"""
        You are tutoting a student right now. 
        Question: {self.config.data.question}
        Student Answer: {self.config.data.answer}
        Level: {self.config.data.level}
        
        Provide feedback (as a teacheer talikng to a student) on accuracy and syllabus alignment. Give feedback:
        -If there anything incorrect in your answer if yes what
        - How to improve 

        No suggestions in the end, all text must be the same font, no emojis.
        """
        #- A better sample answer
        try:
            response = self.client.responses.create(
                model=self.config.model.model_name,
                input = f"""
                You are a strict but helpful Agricultural Science teacher also you are Leaving Certificate Agricultural Science examiner. 
                {user_content}
                """)
            return response.output_text
        
        except Exception as e:
            logger.error(f"Feedback Generation Error: {e}")
            return  "Error generating feedback."


# if __name__ == "__main__":

#     config = AppConfig(
#         model=ModelConfig(model_name=MODEL_NAME, api_key="ollama"),
#         data=DataConfig(),
#         generation=GenerationConfig()
#     ) 
#     generator = QuestionGenerator(config)
#     print(generator.generate_questions())

#     sample_data = DataConfig(
#         question="Explain why strict controls are necessary when applying pesticides to farm crops.",
#         answer="To stop them getting into the water and killing bees."
#     )
#     config1 = AppConfig(
#         model=ModelConfig(model_name=CHAGPT_MODEL, base_url = ""),
#         generation=None,
#         data=DataConfig(question = sample_data.question,answer= sample_data.answer, level=sample_data.level)
#     )
#     generator = FeedbackGenerator(config1)
#     print(generator.generate_feedback())