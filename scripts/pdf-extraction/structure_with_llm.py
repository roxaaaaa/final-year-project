import ollama
import re
import json
import os

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

SOLUTION_PROMPT = """
You are a structured data extractor for Irish Leaving Certificate Agricultural Science exam solutions."""

def process_with_llm(input_pdf_path, output_json_path, is_solution=False):
    with open(input_pdf_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    structured_data = []

    for q in raw_data:
        if is_solution==True:
          print(f"Structuring Solution for Question {q['question_number']}...")
          # For solutions, we want to include the question text as context for better structuring
          full_prompt = SOLUTION_PROMPT + q['solution']
        else:
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
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)
    print(f"Finished. Structured data saved to {output_json_path}")

if __name__ == "__main__":
  # paths
  script_dir = os.path.dirname(os.path.abspath(__file__))
  project_dir = os.path.dirname(os.path.dirname(script_dir))
  # input_path = os.path.join(project_dir, "data", "unstructured", "questions_2023_higher.json")
  # output_path = os.path.join(project_dir, "data", "structured", "structured_question_2023_higher.json")
  range_higher = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]
    
  for i in range_higher:
    json_file = f"questions_{i}_higher.json"
    json_path = os.path.join(project_dir, "data", "unstructured", json_file)
    output_path = os.path.join(project_dir, "data", "structured", f"structured_questions_{i}_higher.json")
    questions = process_with_llm(json_path, output_path, is_solution=False)
