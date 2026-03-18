"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

export default function PracticePage() {
  const [exam, setExam] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const router = useRouter();

  useEffect(() => {
    const saved = localStorage.getItem("currentExam");
    if (saved) {
      try {
        const data = JSON.parse(saved);
        setExam(data);
        //Objects are not valid as a React child" error - ensure questions is an array of strings
        if (data.questions && Array.isArray(data.questions)) {
          setQuestions(data.questions);
        } else {
          console.error("Format error: 'questions' is missing or not an array", data);
        }
        const progress = localStorage.getItem("practice_progress");
        if (progress) {
          try{
            setAnswers(JSON.parse(progress));
          }catch(e){
            console.error("Error parsing practice progress:", e);
          }
        }
      } catch (e) {
        console.error("Error parsing currentExam:", e);
      }
    } else {
      router.push("/");
    }
  }, [router]);
  
  const handleUpdateAnswer = (val) => {
    const newAnswers = { ...answers, [currentIndex]: val };
    setAnswers(newAnswers);
    localStorage.setItem("practice_progress", JSON.stringify(newAnswers));
  };

  if (!exam || questions.length === 0) return <div className="p-20 text-white">Loading Questions...</div>;
  return (
    <div className="min-h-screen bg-slate-900 text-white p-4 sm:p-12 flex flex-col items-center">
      {/* Progress Bar */}
      <div className="w-full max-w-2xl mb-8">
        <div className="flex justify-between text-xs font-bold text-emerald-400 uppercase mb-2">
          <span>Question {currentIndex + 1} of {questions.length}</span>
          <span>{Math.round(((currentIndex + 1) / questions.length) * 100)}% Complete</span>
        </div>
        <div className="h-2 w-full bg-white/10 rounded-full overflow-hidden">
          <div 
            className="h-full bg-emerald-500 transition-all duration-500" 
            style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }}
          ></div>
        </div>
      </div>

      {/* Question Card */}
      <div className="w-full max-w-2xl relative">
        <div className="bg-slate-800 border border-white/10 rounded-3xl p-8 shadow-2xl min-h-[400px] flex flex-col">
          <div className="flex items-center gap-3 mb-6">
            <span className="bg-emerald-500 text-slate-900 font-black px-3 py-1 rounded-lg">
              Question {currentIndex + 1}
            </span>
            <h2 className="text-slate-400 font-medium">Agricultural Science Paper</h2>
          </div>

          <div className="text-xl font-serif leading-relaxed mb-8 text-white">
            {questions[currentIndex]}
          </div>

          <textarea
            className="flex-grow w-full bg-slate-900/50 border-2 border-white/5 rounded-2xl p-5 focus:border-emerald-500 outline-none transition-all text-white placeholder-slate-600 resize-none"
            placeholder="Write your answer here..."
            value={answers[currentIndex] || ""}
            onChange={(e) => handleUpdateAnswer(e.target.value)}
          />

          {/* Navigation Controls */}
          <div className="flex items-center justify-between mt-8 pt-6 border-t border-white/5">
            <button
              disabled={currentIndex === 0}
              onClick={() => setCurrentIndex(prev => prev - 1)}
              className="px-6 py-3 rounded-xl font-bold transition-all disabled:opacity-20 hover:bg-white/5"
            >
              ← Previous
            </button>

            {currentIndex === questions.length - 1 ? (
              <button 
                onClick={() => {
                  // alert("Exam Submitted! Check your localStorage for results.");
                  router.push("/feedback");
                }}
                className="px-10 py-3 bg-emerald-500 text-slate-900 rounded-xl font-black hover:scale-105 transition shadow-lg shadow-emerald-500/40"
              >
                Submit Exam
              </button>
            ) : (
              <button
                onClick={() => setCurrentIndex(prev => prev + 1)}
                className="px-8 py-3 bg-white/10 hover:bg-white/20 rounded-xl font-bold transition-all flex items-center gap-2"
              >
                Next Question →
              </button>
            )}
          </div>
        </div>
      </div>

      <button 
        onClick={() => router.push("/feedback")}
        className="mt-8 text-slate-500 hover:text-white text-sm transition"
      >
        Submit early and see feedback
      </button>
    </div>
  );
}