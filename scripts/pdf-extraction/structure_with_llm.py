import ollama
import re

import json
import ollama
import os

# paths
script_dir = os.path.dirname(os.path.abspath(__file__))
input_path = os.path.join(script_dir, "questions_2024_higher.json")
output_path = os.path.join(script_dir, "structured_question_2024_higher.json")


# Define the Prompt from earlier
QUESTION_PROMPT = """
You are extracting structure from an Irish Leaving Certificate Agricultural Science exam question. 
Return ONLY valid JSON. No preamble, no markdown fences.

Rules:
- Extract question_num, context, and parts array
- Each part has: id, text
- solution is always an empty list []
- If a part references an image/diagram/photography, set skip: true
- If nesting is ambiguous, prefer flatter structure

Schema:
{
  "question_num": "string",
  "context": "string",
  "parts": [
    { "id": "string", "text": "string", "solution": [], "skip": boolean }
  ]
}
Input Text:
"""

def process_with_llm():
    with open(input_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    structured_data = []

    for q in raw_data:
        print(f"Structuring Question {q['question_number']}...")
        
        # Combine prompt with the specific question text
        full_prompt = QUESTION_PROMPT + q['text']
        
        # Call Ollama
        response = ollama.chat(model='qwen2.5-coder', messages=[
            {
                'role': 'user',
                'content': full_prompt,
            },
        ], format='json') # Enforce JSON output

        try:
            structured_q = json.loads(response['message']['content'])
            structured_data.append(structured_q)
        except json.JSONDecodeError:
            print(f"Error parsing JSON for Question {q['question_number']}")

    # Save final result
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)
    print(f"Finished. Structured data saved to {output_path}")

if __name__ == "__main__":
    process_with_llm()