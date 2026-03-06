import json
import os
from pydoc import text
# merge the structured question and solution files into a single file for each year and level

def merge_files(questions_file, solutions_file, output_file):
    with open(questions_file, 'r', encoding='utf-8') as qf:
        questions_data = json.load(qf)
    with open(solutions_file, 'r', encoding='utf-8') as sf:
        solutions_data = json.load(sf)
    
    lookup_map = {}
    for q in questions_data:
        if q.get("skip") is True:
            continue
        q_num = q.get('question_num')
        if q_num is not None:
            for part in q.get('parts', []):
                part_num = part.get('part_num')
                if part_num is not None:
                    lookup_map[f"{q_num}{part_num}"] = part.get("solution", [])
    for s in solutions_data:
        if s.get("skip") is True:
            continue
        if s.get("solutions")==[]:
            continue
        s_num = s.get('question_num')
        if s_num is not None:
            for part in s.get('parts', []):
                part_num = part.get('id')
                if part_num is not None:
                    key = f"{s_num}{part_num}"
                    if key in lookup_map:
                        part['solution'] = lookup_map[key] 
    
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(solutions_data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(os.path.dirname(script_dir)) 
    range_higher = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]

    for i in range_higher:
        questions_file = os.path.join(project_dir, "data", "structured", f"structured_questions_{i}_higher.json")
        solutions_file = os.path.join(project_dir, "data", "structured", f"structured_solutions_{i}_higher.json")
        output_file = os.path.join(project_dir, "data", "merged", f"higher_merged_{i}_.json")
        merge_files(questions_file, solutions_file, output_file)
        print(f"Merged {questions_file} and {solutions_file} into {output_file}")
    
