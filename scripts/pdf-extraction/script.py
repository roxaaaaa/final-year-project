import pdfplumber
import re
import os
import json
from typing import List, Dict, Tuple

script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(script_dir))

ordinary_pdf_path = os.path.join(project_dir, "data", "ordinary")
higher_pdf_path = os.path.join(project_dir, "data", "higher")

SKIP_WORDS = ["image", "picture", "pictures","diagram", " graph ","photograph",  "figure", "illustration",
                     "place a tick", "correct box", "breed of cattle shown", "breed shown"] 

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
        # Find start - look for "Question 1" or just "1." pattern
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and (re.search(r"question\s+1", text, re.IGNORECASE) or 
                        re.search(r"^\s*1\s*\.", text, re.IGNORECASE | re.MULTILINE)):
                start_page = i
                break
        
        # Find end (searching backwards from end for efficiency)
        for i, page in enumerate(reversed(pdf.pages)):
            text = page.extract_text()
            if text and re.search(r"(blank page|acknowledgements)", text, re.IGNORECASE):
                end_page = len(pdf.pages) - i
                break
    
        #print(start_page, ":", end_page)
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
            q_match = re.search(r'Question\s+(\d+)|\b(\d+)\s*\.', text, re.IGNORECASE)
            q_num = q_match.group(1) or q_match.group(2) if q_match else "?"
            print(f"[SKIPPED] Question {q_num}: 'labelled diagram' present but also matched {others}")
            return True
        # Only 'diagram' present and phrase 'labelled diagram' detected - keep
        return False

    #  if any skip keyword appears, skip.
    if present_keywords:
        q_match = re.search(r'Question\s+(\d+)|\b(\d+)\s*\.', text, re.IGNORECASE)
        q_num = q_match.group(1) or q_match.group(2) if q_match else "?"
        print(f"[SKIPPED] Question {q_num}: matched keyword(s) {present_keywords}")
        return True

    return False


def extract_text_from_pdf(pdf_path: str, skip_word: str = None) -> List[Dict]:
    """
    Extracts text from `pdf_path`, splits into question blocks using
    "Question N" boundaries and returns a list of question dicts.

    Blocks matching internal skip heuristics (`_should_skip_question`) are also skipped.
    """
    cleaned_text = ""

    start_page, end_page = get_page_range(pdf_path)
    if end_page == -1:
        end_page = None

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
                cleaned_text += '\n'.join(cleaned_lines) + "\n"

    if re.search(r'Question\s+\d+', cleaned_text, re.IGNORECASE):
        blocks = re.split(r'(?=(?:Question\s+\d+))', cleaned_text, flags=re.IGNORECASE | re.MULTILINE)
    else:
        # split on numbered lines only as a fallback
        blocks = re.split(r'(?=(?:\n\s*\d+\s*\.))', cleaned_text, flags=re.MULTILINE)
    questions: List[Dict] = []

    seen_qnums = set()
    for block in blocks:
        if not block.strip():
            continue

        # Try to match "Question N" first, then try "N." format
        q_match = re.search(r'Question\s+(\d+)', block, re.IGNORECASE)
        if not q_match:
            # Try matching just the number (e.g., "2." at start of line)
            q_match = re.search(r'^\s*(\d+)\s*\.', block, re.MULTILINE)
        
        if not q_match:
            continue

        q_num = int(q_match.group(1))

        # Avoid adding duplicate question numbers
        # or repeated pages cause the same question 
        if q_num in seen_qnums:
            continue
        seen_qnums.add(q_num)

        if _should_skip_question(block):
            continue

        questions.append({
            "question_number": q_num,
            "text": block.strip()
        })
    return questions


def write_questions_to_json(questions: List[Dict], out_path: str):
    with open(out_path, 'w', encoding='utf-8') as fh:
        json.dump(questions, fh, indent=2, ensure_ascii=False)
    
if __name__ == "__main__":
    # Using the defined paths
    pdf_file = "paper_2024.pdf"
    pdf_path = os.path.join(higher_pdf_path, pdf_file)
    text = extract_text_from_pdf(pdf_path)
    for q in text:
        print()
        print(f"{q['question_number']}:\n{q['text']}\n{'-'*40}")


 
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
#     "Environment & Sustainability":{},
#     "Genetics":{}
    
# }    

