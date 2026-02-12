import pdfplumber
import re
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(os.path.dirname(script_dir))

ordinary_pdf_path = os.path.join(project_dir, "data", "ordinary")

# 2025
#stucture of doc: Question number, then a sentance , then options (a)-(e)
# and each such option can have (i)-(v), then the next option or question. 
# each page has the buttom line ORDINARY LEVEL AGRICULTURAL SCIENCE  |  Pre-Leaving Certificate, 2025 and page number 
# skip question with ticking te box, identifying from imgae or diagram

SKIP_WORDS = ["showed", "\uf0fc","image", "following", "from the list" , "picture", "shown", "diagram", "graph", "table", "figure", "illustration", "displayed", "depicted", "represented", "True", "False", "correct", "incorrect", "right", "wrong", "yes", "no"] 

SOFT_SKIP= ["other valid responses", "Answer", "**Accept other valid answers", "Any three valid points"]
HARD_SKIP= ["BLANK PAGE", "Leaving Certificate Examination", "Agricultural Science – Ordinary Level", "Agricultural Science – Higher Level", "ORDINARY LEVEL AGRICULTURAL SCIENCE  |  Pre-Leaving Certificate, 2025", "HIGHER LEVEL AGRICULTURAL SCIENCE  |  Pre-Leaving Certificate, 2025", "Page", "section","ordinary", "higher", "level"]
# add level of question (ordinary, higher), topic, solution.

# \n        → new line
# \s*       → optional spaces
# Question  → literal word
# \s+       → at least one space
# (\d+)     → capture the number (VERY important)
# \s*\n     → optional spaces + newline
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
        # Find Start
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and re.search(r"question 1", text, re.IGNORECASE):
                start_page = i
                break
        
        # Find End (searching backwards from end for efficiency)
        for i, page in enumerate(reversed(pdf.pages)):
            text = page.extract_text()
            if text and re.search(r"(blank page|acknowledgements)", text, re.IGNORECASE):
                end_page = len(pdf.pages) - i
                break
    
        print(start_page, ":", end_page)
    return start_page, end_page

def extract_text_from_pdf(pdf_path):
    
    cleaned_text = ""
    
    with pdfplumber.open(pdf_path) as pdf:
        pages_to_process = pdf.pages      
        
        for page in pages_to_process[get_page_range(pdf_path)[0]:get_page_range(pdf_path)[1]]:
            text = page.extract_text()
            if text:
                cleaned_lines = []
                lines = text.split('\n')
                for line in lines:
                    if any(h.lower() in line.lower() for h in HARD_SKIP):
                        continue
                    for skip in SOFT_SKIP:
                        pattern = re.escape(skip)
                        line = re.sub(pattern, '', line, flags=re.IGNORECASE)
                    line = " ".join(line.split())  # normalize spacing
                    if line:   # avoid empty lines
                        cleaned_lines.append(line)
                cleaned_lines = list(dict.fromkeys(cleaned_lines)) # remove duplicates while preserving order
                cleaned_text += '\n'.join(cleaned_lines) + "\n"
    return cleaned_text
    
if __name__ == "__main__":
    # Using the defined paths
    pdf_file = "paper_2024.pdf"
    pdf_path = os.path.join(ordinary_pdf_path, pdf_file)
    text = extract_text_from_pdf(pdf_path)
    print("Extracted Text:")
    print(text[:2000]) 
    # questions = extract_question_from_text(text[:1000])
    # print(questions)   
 
# def extract_topic(text):
#     text = text.lower()
#     for topic, keywords in TOPIC_KEYWORDS.items():
#         if any(keyword in text for keyword in keywords["primary"]):
#             return topic
#     return "General"

# def extract_question_from_text(text):
#     questions = []

#     # 1. Split by Question Number using lookahead
#     blocks = re.split(r'(?=\n\s*Question\s+\d+)', text)

#     for block in blocks:
#         # Extract Question Number
#         q_match = re.search(r'Question\s+(\d+)', block)
#         if not q_match:
#             continue
        
#         q_num = q_match.group(1)
        
#         # 2. Split by sub-questions (a), (b), (c)
#         # Added handling for variations in numbering like (i), (ii)
#         parts = re.split(r'\n\s*[\(\[]([a-zivx]+)[\)\]]\s+', block)
        
#         # The text before sub-question (a)
#         main_context = parts[0].replace(f"Question {q_num}", "").strip()

#         for j in range(1, len(parts), 2):
#             sub_letter = parts[j]
#             sub_content = parts[j + 1]

#             # 3. Clean special characters (ticks, etc.)
#             sub_content = sub_content.replace('\uf0fc', '').strip()
            
#             # Skip if contains skip keywords
#             cleaned_content = re.sub(r'[^\w\s]', '', sub_content).lower()
#             if any(word.lower() in cleaned_content for word in SKIP_WORDS):
#                 continue

#             # 4. Refined Solution/Question splitting
#             lines = sub_content.strip().split('\n')
#             question_lines = []
#             solution_lines = []
#             in_solution = False
            
#             for line in lines:
#                 # If a line starts with a dash or is just marks (e.g., 2m), it's likely a solution
#                 if re.match(r'^\s*[–-]', line) or re.search(r'\(\d+m\)', line) or re.search(r'\d+\s*[xX]\s*\d+m', line):
#                     in_solution = True
                
#                 if in_solution:
#                     solution_lines.append(line.strip())
#                 else:
#                     question_lines.append(line.strip())
                
#             question_text = ' '.join(question_lines).strip()
#             solution_text = '\n'.join(solution_lines).strip()

#             if question_text:
#                 q_obj = {
#                     "id": f"q{q_num}_{sub_letter}",
#                     "question_number": int(q_num),
#                     "sub_question": sub_letter,
#                     "question_text": question_text,
#                     "solution": solution_text,
#                     "context": main_context
#                 }
#                 questions.append(q_obj)
        
#     return questions


TOPIC_KEYWORDS = {
    "Animals": {
        "primary": ["breed", "cattle", "sheep", "pig", "livestock", "dairy", "beef", 
                   "calving", "mastitis", "BCS", "gestation", "oestrus"],
        "secondary": ["animal welfare", "herd", "flock", "fertility"]
    },
    "Soil": {
        "primary": ["soil", "pH", "texture", "sand", "silt", "clay", "fertility"],
        "secondary": ["nutrients", "drainage", "erosion"]
    },
    "Crops": {
        "primary": ["seed", "germination", "photosynthesis", "crop", "weed"],
        "secondary": ["plant growth", "harvest", "planting"]
    },
    "Scientific Practices":{},
    "Environment & Sustainability":{},
    "Genetics":{}
    
}    

