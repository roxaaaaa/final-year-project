import ollama
import re
import json
import os

import pdfplumber

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
      "skip": boolean,           // true if this part requires an image/diagram/true/false to answer
      "subparts": [              
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
-- in case of (i) Explain the following terms: 
                  1. Moisture stress 
                  2. Permanent wilting point. Keep sub-item 1. 2. in the text of part (i) rather than creating a new subpart level 

## SKIP RULES — set skip: true when the part/question:

- References a diagram, photograph, image, figure, chart, or table shown below/above/attached
- Uses phrases like: "identify from ...", "shown below", "in the photograph", "illustrated above",
  "refer to the diagram", "label the diagram", "in Figure X", "from the image", 
  "as shown", "true/false", "tick the correct box", "complete the table", "fill in the blanks"
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
PROMPT_2025 = """You are a precision data extraction engine. Your task is to convert raw Irish Leaving Certificate Agricultural Science exam questions and solutions into a structured JSON format.

### OUTPUT JSON SCHEMA
{
  "question_num": "string",    // Digit only: "1", "5", "7"
  "context": "string",         // Shared introductory text or ""
  "skip": boolean,             // true if question relies on an image/diagram/table/photo
  "parts": [
    {
      "id": "string",          // Lowercase letter: "a", "b", "c"
      "text": "string",        // The question text ONLY
      "solution": ["string"],  // Array of valid answer points (cleaned)
      "skip": boolean,         // true if this part refers to an image/diagram
      "subparts": [            // ONLY if roman numerals (i, ii) are present
        {
          "id": "string",      // Roman numeral: "i", "ii", "iii"
          "text": "string",
          "solution": ["string"],
          "skip": boolean
        }
      ]
    }
  ]
}

### EXTRACTION & CLEANING RULES
1.  **Identify IDs**: 
    - Questions: "Question 1" -> "1".
    - Parts: "(a)" -> "a".
    - Subparts: "(i)" -> "i".
2.  **Handle "OR" Questions**: If the source says "Question 1 (a) OR (b)", treat them as distinct entries in the "parts" array (id: "a" and id: "b").
3.  **Clean Solutions**: 
    - Strip marking schemes like "5 x 2m = 10m" or "2 x 2m = 4m".
    - Strip internal instructional text like "**Accept other valid s".
    - Extract the actual answer text which usually follows a dash (–), a colon (:), or is listed in the "solution" field.
4.  **Set "skip": true if text contains**: 
    - "Identify", "shown", "diagram", "photograph", "image", "table", "chart", "graph", "below", "above", "fill in the blanks", "true/false".
5.  **Context**: If a piece of text applies to both (a) and (b), put it in "context". Otherwise, keep "context" as "".
6.  **Formatting**: Return ONLY valid JSON. No markdown code fences, no preamble.

### INPUT DATA"""

SOLUTION_PROMPT = """
You are a structured data extractor for Irish Leaving Certificate Agricultural Science exam solutions."""

def process_with_llm(input_pdf_path, output_json_path, prompt):
    with open(input_pdf_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    structured_data = []

    for q in raw_data:
        full_prompt = prompt + q['text']
        
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
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)
    print(f"Finished. Structured data saved to {output_json_path}")

if __name__ == "__main__":
  script_dir = os.path.dirname(os.path.abspath(__file__))
  project_dir = os.path.dirname(os.path.dirname(script_dir)) 

  input_json_path = os.path.join(project_dir, "data", "unstructured", "questions_2025_higher.json")
  output_json_path = os.path.join(project_dir, "data", "structured", "structured_questions_2025_higher.json")
  process_with_llm(input_json_path, output_json_path, QUESTION_PROMPT)
  