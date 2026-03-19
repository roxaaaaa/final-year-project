"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

export default function PracticePage() {
  const [questions, setQuestions] = useState([]);
  const [examLevel, setExamLevel] = useState(""); 
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [feedback, setFeedback] = useState({});
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const saved = localStorage.getItem("currentExam");
    if (saved) {
      try {
        const data = JSON.parse(saved);
        setQuestions(data.questions || []);
        setExamLevel(data.level);
      } catch (e) {
        console.error("Error parsing exam:", e);
      }
    } else {
      router.push("/");
    }
  }, [router]);

  const handleUpdateAnswer = (val) => {
    setAnswers({ ...answers, [currentIndex]: val });
  };

  const submitForFeedback = async () => {
    const currentAnswer = answers[currentIndex];
    if (!currentAnswer || currentAnswer.trim() === "") {
      return alert("Please write something first!");
    }

    setLoading(true);
    try {
      const response = await fetch("http://localhost:8000/api/ai/generate_feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // MATCHING BACKEND: { question: str, answer: str, level: str }
        body: JSON.stringify({
          question: questions[currentIndex],
          answer: currentAnswer,
          level: examLevel, 
        }),
      });

      if (!response.ok) throw new Error("Failed to get feedback");

      const data = await response.json();
      // Store feedback for the current question index
      setFeedback({ ...feedback, [currentIndex]: data.feedback });
    } catch (err) {
      console.error("Feedback Error:", err);
      setFeedback({ ...feedback, [currentIndex]: "Could not reach the teacher. Please try again." });
    } finally {
      setLoading(false);
    }
  };

  if (questions.length === 0) return <div className="p-20 text-white">Loading...</div>;

  const currentHasFeedback = !!feedback[currentIndex];

  return (
    <div className="min-h-screen bg-slate-900 text-white p-4 sm:p-12 flex flex-col items-center">
      {/* Progress Bar */}
      <div className="w-full max-w-2xl mb-8">
        <div className="flex justify-between mb-2 text-sm text-slate-400">
            <span>{examLevel.toUpperCase()} LEVEL</span>
            <span>{currentIndex + 1} of {questions.length}</span>
        </div>
        <div className="h-1.5 w-full bg-white/10 rounded-full">
          <div
            className="h-full bg-emerald-500 transition-all duration-500"
            style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }}
          ></div>
        </div>
      </div>

      <div className="w-full max-w-2xl bg-slate-800 border border-white/10 rounded-3xl p-8 shadow-2xl">
        <div className="mb-6">
          <span className="text-emerald-400 font-bold text-sm uppercase tracking-widest">Question {currentIndex + 1}</span>
          <p className="text-xl font-serif mt-2">{questions[currentIndex]}</p>
        </div>

        <textarea
          disabled={currentHasFeedback || loading}
          className="w-full bg-slate-900/50 border-2 border-white/5 rounded-2xl p-5 focus:border-emerald-500 outline-none transition-all min-h-[150px] disabled:opacity-50"
          placeholder="Type your answer here..."
          value={answers[currentIndex] || ""}
          onChange={(e) => handleUpdateAnswer(e.target.value)}
        />

        {/* Feedback Display Area */}
        {currentHasFeedback && (
          <div className="mt-6 p-5 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl animate-in fade-in slide-in-from-bottom-2">
            <h4 className="text-emerald-400 font-bold mb-2 flex items-center gap-2">
              <span>Teacher Feedback:</span>
            </h4>
            <p className="text-slate-300 leading-relaxed text-sm whitespace-pre-wrap">
              {feedback[currentIndex]}
            </p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-4 mt-8">
          {!currentHasFeedback ? (
            <button
              onClick={submitForFeedback}
              disabled={loading || !answers[currentIndex]}
              className="flex-1 py-4 bg-emerald-500 text-slate-900 rounded-xl font-black hover:bg-emerald-400 transition disabled:opacity-50"
            >
              {loading ? "Analyzing Answer..." : "Check My Answer"}
            </button>
          ) : (
            <button
              onClick={() => {
                if (currentIndex < questions.length - 1) {
                  setCurrentIndex(prev => prev + 1);
                } else {
                  router.push("/complete");
                }
              }}
              className="flex-1 py-4 bg-white/10 hover:bg-white/20 rounded-xl font-bold transition"
            >
              {currentIndex === questions.length - 1 ? "Finish Exam" : "Next Question →"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}