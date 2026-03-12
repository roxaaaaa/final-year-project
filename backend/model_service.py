from typing import Optional, Literal, List

import ollama
import json
from openai import Client, OpenAI
import logging
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_NAME = "llama3.1:8b"
HIGHER_EXAMPLE_QUESTIONS = """
            Q: "Give three reasons for the practice of thinning forest trees.",
            Q: "Explain why strict controls are necessary when applying pesticides to farm crops.",
            Q: "Mention three factors that contribute to the formation of a gley soil."
        """
ORDINARY_EXAMPLE_QUESTIONS = """
        Q: Define the term biological control.
        Q: Crop rotation is a common practice on Irish tillage farms. Explain the underlined term. State two advantages of crop rotation.
        Q: Suggest three ways in which farmers can control / prevent liver fluke on their farm."""

SYSTEM_PROMPT = "You are a Leaving Cert Agricultural Science examiner. Output only the final exam question. Do not show reasoning."
        

@dataclass
class ModelConfig:
    model_name: str = MODEL_NAME
    base_url: str ="http://localhost:11434/v1"

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


class QuestionGenerator:
    #This parameter can be either a GenerationConfig object OR None
    def __init__(self, config: Optional[AppConfig] = None):
        """
        Initialize the QuestionGenerator with the given configuration.
        Args:
            config (GenerationConfig): Configuration for question generation.
        """
        self.config = config or AppConfig(model=ModelConfig(), generation=GenerationConfig(), task=QuestionTaskConfig())
        self.client = Client(base_url=self.config.model.base_url, api_key="ollama")  # No API key needed for local Ollama

    def generate_questions(self, num_questions: Optional[int] = None) -> List[str]:
        """
        Generate agricultural science exam questions
        
        Args:
            num_questions: Number of questions to generate
            
        Returns:
            List of generated questions
        """
        num_questions = num_questions or self.config.generation.num_questions
        questions = []
    
        for i in range(num_questions):
            prompt = f"""Generate a {self.config.task.level} level Agricultural Science exam question on the topic of {self.config.task.topic}.
            Example questions:
            {HIGHER_EXAMPLE_QUESTIONS if self.config.task.level == "higher" else ORDINARY_EXAMPLE_QUESTIONS}
            Now generate a new question. Q:"""
            
            try:
                response = self.client.chat.completions.create(
                    model=self.config.model.model_name,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.config.generation.max_tokens,
                    temperature=self.config.generation.temperature,
                )
                question = response.choices[0].message.content
                questions.append(question)
                logger.info(f"Generated question: {question}")
            except Exception as e:
                logger.error(f"Error generating question: {e}")
        return questions

if __name__ == "__main__":
    print("Starting question generation...")

    config_higher = AppConfig(
        model=ModelConfig(model_name=MODEL_NAME),
        generation=GenerationConfig(),
        task=QuestionTaskConfig(level="higher")
    )
    print(config_higher.task.level)
    generator = QuestionGenerator(config_higher)
    generated_questions = generator.generate_questions()
    print("="*20)
    print(f"Generated {config_higher.task.level} Questions:")
    for q in generated_questions:
        print(q)

    config_ordinary = AppConfig(
        model=ModelConfig(model_name=MODEL_NAME),
        generation=GenerationConfig(),
        task=QuestionTaskConfig(level="ordinary")
    )
    print(config_ordinary.task.level)
    generator = QuestionGenerator(config_ordinary)
    generated_questions = generator.generate_questions()
    print("="*20)
    print(f"Generated {config_ordinary.task.level} Questions:")
    for q in generated_questions:
        print(q)