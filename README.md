# final-year-project
# AgriGen AI: Intelligent Leaving Cert Agricultural Science Tutor 🐄🌾

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![NLP](https://img.shields.io/badge/NLP-BART--SQuAD-orange.svg)
![AI](https://img.shields.io/badge/OpenAI-Reasoning-green.svg)
![Platform](https://img.shields.io/badge/Platform-Web-lightgrey.svg)

## 📖 Project Overview

This project is a specialized intelligent educational application tailored specifically for the **Irish Leaving Certificate Agricultural Science** curriculum. 

General-purpose AI models (like ChatGPT) are often too broad and can lack the precision or "neutrality" required for specific state examinations. **AgriGen AI** solves this by using a fine-tuned **BART-SQuAD-QA** model, trained on a custom dataset of past Irish examination papers and marking schemes. This ensures that the questions generated align perfectly with the phrasing, structure, and difficulty standards of Higher and Ordinary levels.

The system also features an **AI Avatar** that provides verbal feedback, transforming a static revision tool into an interactive, human-like tutoring environment.

---

## 🌟 Key Features

### For Teachers 🧑‍🏫
*   **Automated Question Generation:** Instantly create unique, curriculum-aligned questions based on specific topics.
*   **Exam Phrasing:** Questions mimic the official SEC (State Examinations Commission) style.
*   **Export Functionality:** Export generated question sets and marking schemes into **PDF** or **DOCX** formats for classroom tests.

### For Students 🎓
*   **Interactive Practice:** Answer questions in real-time and receive immediate, high-quality feedback.
*   **AI Judging Engine:** Powered by OpenAI, the system understands the *meaning* behind answers, awarding marks even if the phrasing differs from the marking scheme.
*   **AI Avatar & TTS:** An animated persona delivers feedback verbally using Text-to-Speech, increasing engagement and retention.

---

## ⚙️ Technical Architecture

The system utilizes a hybrid AI approach to ensure both accuracy and reasoning capability:

1.  **Content Generation (Local Model):** 
    *   A fine-tuned **BART-SQuAD-QA** model.
    *   Trained on a curated dataset of Irish Agricultural Science past papers (Higher & Ordinary).
    *   Ensures domain-specific accuracy and SEC-style phrasing.
2.  **Reasoning & Feedback (OpenAI API):**
    *   Acts as the "Judging Engine."
    *   Compares student inputs against the official marking scheme to provide human-like, constructive feedback.
3.  **Visual Interaction:**
    *   Integrated AI Avatar that converts text-based feedback into spoken audio and synchronized animation.

---

## 🛠 Tech Stack

*   **Language:** Python
*   **NLP Models:** BART (Fine-tuned), OpenAI GPT API
*   **Data Handling:** SQuAD-formatted custom Agricultural Science dataset
*   **Document Generation:** `python-docx`, `ReportLab` (for PDF)
*   **Methodology:** Agile Development (Iterative testing and refinement)

---

## 🚀 Installation & Setup

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/roxaaaaa/final-year-project.git
    cd final-year-project
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set Up API Keys:**
    Create a `.env` file in the root directory and add your OpenAI credentials:
    ```env
    OPENAI_API_KEY=your_api_key_here
    ```

4.  **Run the Application:**
    ```bash
    npm run dev
    uvicorn server --reload
    ```

---

## 📂 Dataset Details

The system is trained on a specialized dataset created specifically for this project:
*   **Sources:** Irish State Examination past papers (2010–Present).
*   **Content:** Questions, Model Solutions, and official Marking Schemes for Agricultural Science.
*   **Format:** Fine-tuned using the SQuAD (Stanford Question Answering Dataset) format for high precision in educational contexts.

---

## 🧪 Development Methodology

This project follows the **Agile Methodology**. This allows for:
*   Continuous integration of new exam data.
*   Iterative testing of the BART model to ensure question difficulty is balanced.
*   Regular refinement of the AI Avatar's interaction logic based on user feedback.

---
*Disclaimer: This tool is intended for revision purposes and is designed to supplement, not replace, official curriculum materials provided by the SEC.*
