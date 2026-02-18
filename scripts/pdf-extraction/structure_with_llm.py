import ollama
import re
import json
import os

# paths
script_dir = os.path.dirname(os.path.abspath(__file__))
input_path = os.path.join(script_dir, "questions_2023_ordinary.json")
output_path = os.path.join(script_dir, "structured_question_2023_ordinary.json")


# Define the Prompt from earlier
QUESTION_PROMPT = """
You are a structured data extractor for Irish Leaving Certificate Agricultural Science exam questions.
Return ONLY valid JSON. No preamble, no explanation, no markdown fences.

## OUTPUT SCHEMA

{
  "question_num": "string",      // e.g. "1", "2", "3"
  "context": "string",           // shared intro text before parts, or "" if none
  "skip": boolean,               // true if the question-level context references an image/diagram
  "parts": [
    {
      "id": "string",            // e.g. "a", "b", "c"
      "text": "string",
      "solution": [],
      "skip": boolean,           // true if this part requires an image/diagram to answer
      "subparts": [              // omit if empty
        {
          "id": "string",        // e.g. "i", "ii", "iii"
          "text": "string",
          "solution": [],
          "skip": boolean
        }
      ]
    }
  ]
}

## ID FORMAT RULES (strictly follow)

- Question number: bare digit(s) only — "1", "2", "12"  NOT "Q1", "Question 2", "Q.3"
- Part IDs: single lowercase letter — "a", "b", "c"  NOT "(a)", "a)", "part_a", "part one"
- Subpart IDs: roman numerals only — "i", "ii", "iii", "iv"  NOT "b_i", "(ii)", "1", "2"
- NEVER use words like "part", "section", "question" as an ID value

## STRUCTURE RULES

- Three levels max: question → parts (a/b/c) → subparts (i/ii/iii)
- Prefer flat structure; only create subparts if the source explicitly uses roman numerals
- Do not invent levels that are not in the source text

## SKIP RULES — set skip: true when the part/question:

- References a diagram, photograph, image, figure, chart, or table shown below/above/attached
- Uses phrases like: "identify from ...", "shown below", "in the photograph", "illustrated above",
  "refer to the diagram", "label the diagram", "in Figure X", "from the image", "as shown"
- Cannot be meaningfully answered without seeing a visual element
- If the whole question context requires an image, set skip: true at question level AND on each affected part

## OMISSION RULES — do not include in text:

- Answer-choice instructions: "Answer any two", "Answer either (a) or (b)", "Answer three of the following"
- Section headings or exam instructions that are not part of the question itself

## EXAMPLE INPUT

Question 2
A named soil horizon is shown in the diagram below.
(a) Identify the soil horizon shown.
(b) Describe two characteristics of this horizon.
  (i) Characteristic one:
  (ii) Characteristic two:
(c) Explain the importance of soil pH in crop production.

## EXAMPLE OUTPUT

{
  "question_num": "2",
  "context": "A named soil horizon is shown in the diagram below.",
  "skip": true,
  "parts": [
    { "id": "a", "text": "Identify the soil horizon shown.", "solution": [], "skip": true },
    {
      "id": "b",
      "text": "Describe two characteristics of this horizon.",
      "solution": [],
      "skip": false,
      "subparts": [
        { "id": "i",  "text": "Characteristic one:", "solution": [], "skip": false },
        { "id": "ii", "text": "Characteristic two:", "solution": [], "skip": false }
      ]
    },
    { "id": "c", "text": "Explain the importance of soil pH in crop production.", "solution": [], "skip": false }
  ]
}
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