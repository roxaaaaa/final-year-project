import pdfplumber
import re
import os
import json
from typing import List, Dict, Tuple

script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(script_dir))

ordinary_pdf_path = os.path.join(project_dir, "data", "initial","ordinary")
higher_pdf_path = os.path.join(project_dir, "data", "initial","higher")

SKIP_WORDS = ["image", "picture","diagram", " graph ","photograph",  "figure", "illustration",
                     "a tick", "correct box", "table", "True", "False", "shown below"] 

SOFT_SKIP= ["other valid responses", "Answer", "**Accept other valid answers", "Any three valid points"]
HARD_SKIP= ["BLANK PAGE", "Question 1 carries 60 marks", "Leaving Certificate Examination", "Agricultural Science – Ordinary Level", "Agricultural Science – Higher Level", "ORDINARY LEVEL AGRICULTURAL SCIENCE  |  Pre-Leaving Certificate, 2025", "HIGHER LEVEL AGRICULTURAL SCIENCE  |  Pre-Leaving Certificate, 2025", "Page", "section","ordinary", "higher", "level"]
# json file structure : paper_id level of question (ordinary, higher), question number, context, *topic, id item(a,b,c or ai, aii, biii), text, solution, marks.

def get_page_range(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        """
    Analyzes the PDF to find the page numbers where actual 
    exam content begins and ends.
    """
    start_page = 0
    end_page = -1 
    # Default to last page

    with pdfplumber.open(pdf_path) as pdf:
        # Find start - "Question 1" or just "1." pattern for offical papers and Q1 or Q 1 for the solutions
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and (re.search(r"question\s+1", text, re.IGNORECASE) or 
                        re.search(r"^\s*1\s*\.", text, re.IGNORECASE | re.MULTILINE) or 
                        re.search(r"q\s?1", text, re.IGNORECASE)):   
                start_page = i
                break
        
        # Find end (searching backwards from end for efficiency)
        for i, page in enumerate(reversed(pdf.pages)):
            text = page.extract_text()
            if text and re.search(r"(blank page|acknowledgements)", text, re.IGNORECASE):
                end_page = len(pdf.pages) - i
                break
        
        # fix bug page range [11:5] 
        # if end_page is invalid (before start_page), ignore it
    
        if end_page != -1 and end_page <= start_page:
            end_page = -1
        
        # print(f"[DEBUG get_page_range] Total PDF pages: {len(pdf.pages)}, start: {start_page}, end: {end_page}")
    return start_page, end_page

def _should_skip_question(text: str) -> bool:
    """Check if a question should be skipped based on image/diagram/shown/list keywords.
    
    Special case:
    - Only the exact phrase "labelled diagram" is allowed (KEEP)
    - If "labelled" and "diagram" are in the same question but different parts or have words between them → SKIP
    - If "diagram" appears without "labelled" as a phrase - SKIP
    - All other keywords in SKIP_WORDS also trigger skip
    """
    text_lower = text.lower()

    # Normalize skip keywords (strip extra spaces from list entries)
    present_keywords = [kw.strip() for kw in SKIP_WORDS if kw.strip() and kw.strip() in text_lower]


    if "labelled diagram" in text_lower:
        others = [kw for kw in present_keywords if kw != "diagram"]
        if others:
            q_match = re.search(r'Question\s+(\d+)|\b(\d+)\s*\.|Q\s?\d+', text, re.IGNORECASE)
            q_num = q_match.group(1) or q_match.group(2) if q_match else "?"
            print(f"[SKIPPED] Question {q_num}: 'labelled diagram' present but also matched {others}")
            return True
        # Only 'diagram' present and phrase 'labelled diagram' detected - keep
        return False

    #  if any skip keyword appears, skip.
    if present_keywords:
        q_match = re.search(r'Question\s+(\d+)|\b(\d+)\s*\.|Q\s?\d+', text, re.IGNORECASE)
        q_num = q_match.group(1) or q_match.group(2) if q_match else "?"
        print(f"[SKIPPED] Question {q_num}: matched keyword(s) {present_keywords}")
        return True

    return False


def extract_text_from_pdf(pdf_path: str, is_solution: bool = False) -> List[Dict]:
    """
    Extracts text from `pdf_path`, splits into question blocks using
    "Question N" boundaries and returns a list of question dicts.

    Blocks matching internal skip heuristics (`_should_skip_question`) are also skipped.
    Set is_solution=True to skip aggressive filtering for solution papers.
    """
    cleaned_text = ""

    start_page, end_page = get_page_range(pdf_path)
    if end_page == -1:
        end_page = None
    
    # print(f"[DEBUG] PDF path: {pdf_path}")
    # print(f"[DEBUG] Page range: {start_page}:{end_page}")

    with pdfplumber.open(pdf_path) as pdf:
        pages = pdf.pages[start_page:end_page]
        for page in pages:
            text = page.extract_text()
            if not text:
                continue

            cleaned_lines = []
            lines = text.split('\n')
            for line in lines:
                if any(h.lower() in line.lower() for h in HARD_SKIP):
                    continue
                for skip in SOFT_SKIP:
                    pattern = re.escape(skip)
                    line = re.sub(pattern, '', line, flags=re.IGNORECASE)
                line = " ".join(line.split())
                if line:
                    cleaned_lines.append(line)

            # remove duplicates while preserving order
            cleaned_lines = list(dict.fromkeys(cleaned_lines))
            if cleaned_lines:
                cleaned_text += ' '.join(cleaned_lines) + " "

    regex_pattern = r'(?=(?:Question\s+\d+|Q\s?\d+))'
    if re.search(regex_pattern, cleaned_text, re.IGNORECASE):
        blocks = re.split(r'(?=(?:Question\s+\d+|Q\s?\d+))', cleaned_text, flags=re.IGNORECASE)
    else:
        # Fallback: Split on "1. ", "2. ", etc., but only if it's the start of a section
        blocks = re.split(r'(?=\b\d+\s*\.\s+)', cleaned_text)
    # Show first 500 chars of cleaned text for debugging
    # print(f"[DEBUG] First 500 chars of cleaned_text:\n{cleaned_text[:500]}\n")
    questions: List[Dict] = []

    last_q_num = -1  # Track the last successfully added question number

    for block in blocks:
        block_stripped = block.strip()
        if not block_stripped:
            continue

        # 1. Extract the number using your regex patterns
        q_match = re.search(r'Question\s+(\d+)|Q\s?(\d+)', block_stripped, re.IGNORECASE)
        if not q_match:
            q_match = re.search(r'^\s*(\d+)\s*\.', block_stripped, re.MULTILINE)

        if not q_match:
            # If no number found, append to previous question if it exists
            if questions:
                key = "solution" if is_solution else "text"
                questions[-1][key] += " " + block_stripped
            continue

        # 2. Parse the found number
        try:
            current_q_num = int(q_match.group(1) or q_match.group(2) or q_match.group(0).strip().replace('.', ''))
        except (ValueError, AttributeError):
            continue

        if current_q_num > 20:
            continue
        # 3. SEQUENCE CHECK: If the new number is not greater than the last, 
        # it is likely a sub-item (e.g., Q1 -> Q2 -> 1.1).
        if current_q_num <= last_q_num:
            if questions:
                key = "solution" if is_solution else "text"
                questions[-1][key] += " " + block_stripped
                print(f"[DEBUG] Sub-item detected (Q{current_q_num} <= Q{last_q_num}). Appending to Q{last_q_num}.")
            continue

        # 4. Filter and Add new question
        if not is_solution and _should_skip_question(block_stripped):
            continue

        key = "solution" if is_solution else "text"
        questions.append({
            "question_number": current_q_num,
            key: block_stripped
        })
        
        last_q_num = current_q_num # Update the sequence tracker
        print(f"[DEBUG] Added Question {current_q_num}")
    return questions


def write_questions_to_json(questions: List[Dict], out_path: str):
    with open(out_path, 'w', encoding='utf-8') as fh:
        json.dump(questions, fh, indent=2, ensure_ascii=False)
    
if __name__ == "__main__":
    # Using the defined paths
    pdf_file1 = "paper_2015.pdf"
    pdf_path1 = os.path.join(higher_pdf_path, pdf_file1)
    questions = extract_text_from_pdf(pdf_path1, is_solution=False)
    
    output_path = os.path.join(project_dir, "data", "unstructured", "questions_2015_higher.json")
    write_questions_to_json(questions, output_path)
    print(f"Extracted {len(questions)} questions to {output_path}")

    # pdf_file = "2024.pdf"
    # pdf_path = os.path.join(ordinary_pdf_path, pdf_file)
    # solutions = extract_text_from_pdf(pdf_path, is_solution=True)


    # output_path_solutions = os.path.join(project_dir, "data", "unstructured","solutions_2024_ordinary.json")
    # write_questions_to_json(solutions, output_path_solutions)
    # print(f"Extracted {len(solutions)} solutions to {output_path_solutions}")

 
# def extract_topic(text):
#     text = text.lower()
#     for topic, keywords in TOPIC_KEYWORDS.items():
#         if any(keyword in text for keyword in keywords["primary"]):
#             return topic
#     return "General"

# TOPIC_KEYWORDS = {
#     "Animals": {
#         "primary": ["breed", "cattle", "sheep", "pig", "livestock", "dairy", "beef", 
#                    "calving", "mastitis", "BCS", "gestation", "oestrus"],
#         "secondary": ["animal welfare", "herd", "flock", "fertility"]
#     },
#     "Soil": {
#         "primary": ["soil", "pH", "texture", "sand", "silt", "clay", "fertility"],
#         "secondary": ["nutrients", "drainage", "erosion"]
#     },
#     "Crops": {
#         "primary": ["seed", "germination", "photosynthesis", "crop", "weed"],
#         "secondary": ["plant growth", "harvest", "planting"]
#     },
#     "Scientific Practices":{},
#     "General": {}
# }    

