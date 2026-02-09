import pdfplumber
import re
import os

project_dir = os.path.dirname(os.path.abspath(__file__))

ordinary_pdf_path = os.path.join(project_dir, "ordinary")

# 2025
#stucture of doc: Qestion number, then a sentance , then options (a)-(e)
# and each such option can have (i)-(v), then the next option or question. 
# each page has the buttom line ORDINARY LEVEL AGRICULTURAL SCIENCE  |  Pre-Leaving Certificate, 2025 and page number 
# skip question with ticking te box, identifying from imgae or diagram

SKIP_WORDS = ["showed", "\uf0fc","image", "following", "from the list" , "picture", "shown", "diagram", "graph", "table", "figure", "illustration", "displayed", "depicted", "represented", "True", "False", "correct", "incorrect", "right", "wrong", "yes", "no"] 

SOFT_SKIP= ["other valid responses", "Answer", "– **Accept other valid answers", "Any three valid points"]
HARD_SKIP= ["ORDINARY LEVEL AGRICULTURAL SCIENCE  |  Pre-Leaving Certificate, 2025", "HIGHER LEVEL AGRICULTURAL SCIENCE  |  Pre-Leaving Certificate, 2025", "Page", "section","ordinary", "higher", "level"]
# add level of question (ordinary, higher), topic, solution.

TOPIC_KEYWORDS = {
    "Animal_Production": {
        "primary": ["breed", "cattle", "sheep", "pig", "livestock", "dairy", "beef", 
                   "calving", "mastitis", "BCS", "gestation", "oestrus"],
        "secondary": ["animal welfare", "herd", "flock", "fertility"]
    },
    "Grassland_Management": {
        "primary": ["grass", "pasture", "silage", "grazing", "ryegrass", "clover"],
        "secondary": ["reseeding", "conservation", "harvest"]
    },
    "Soil_Science": {
        "primary": ["soil", "pH", "texture", "sand", "silt", "clay", "fertility"],
        "secondary": ["nutrients", "drainage", "erosion"]
    },
    "Crop_Science": {
        "primary": ["seed", "germination", "photosynthesis", "crop", "weed"],
        "secondary": ["plant growth", "harvest", "planting"]
    },
    "Plant_Biology": {
        "primary": ["osmosis", "chloroplast", "photosynthesis", "chlorophyll", "cell"],
        "secondary": ["organelle", "pigment", "membrane"]
    }
}

# \n        → new line
# \s*       → optional spaces
# Question  → literal word
# \s+       → at least one space
# (\d+)     → capture the number (VERY important)
# \s*\n     → optional spaces + newline

def extract_text_from_pdf(pdf_path):
    
    cleaned_text = ""
    
    with pdfplumber.open(pdf_path) as pdf:
        # Extract year from filename
        filename = os.path.basename(pdf_path)
        year = filename.split('.')[0]  # e.g., "2018" from "2018.pdf"
        # Set page offset based on year
        if year in ['2014', '2015', '2016', '2017', '2018', '2019']:
            pages_to_process = pdf.pages[4:]
        elif year == '2021':
            pages_to_process = pdf.pages[10:]
        elif year in ['2023', '2024']:
            pages_to_process = pdf.pages[11:]
        elif year == '2020':
            pages_to_process = pdf.pages[2:]
        else:
            pages_to_process = pdf.pages
        
        for page in pages_to_process:
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
    pdf_file = "2015.pdf"
    pdf_path = os.path.join(ordinary_pdf_path, pdf_file)
    text = extract_text_from_pdf(pdf_path)
    print("Extracted Text:")
    print(text[:2000])  # Print first 2000 characters of extracted text
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


    

