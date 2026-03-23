"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

export default function PracticePage() {
  const [questions, setQuestions] = useState([]);
  const [examLevel, setExamLevel] = useState("ordinary");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [feedback, setFeedback] = useState({});
  const [videoUrls, setVideoUrls] = useState({});
  const [loading, setLoading] = useState(false);
  const [videoGenerating, setVideoGenerating] = useState(false);
  const [error, setError] = useState(null);
  const router = useRouter();

  // Load exam from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem("currentExam");
    if (saved) {
      try {
        const data = JSON.parse(saved);
        setQuestions(data.questions || []);
        setExamLevel(data.level);
      } catch (e) {
        console.error("Error parsing exam:", e);
        setError("Failed to load exam. Please try again.");
        router.push("/");
      }
    } else {
      router.push("/");
    }
  }, [router]);

  const handleUpdateAnswer = (val) => {
    setAnswers({ ...answers, [currentIndex]: val });
    setError(null);
  };

  const submitForFeedback = async () => {
    const currentAnswer = answers[currentIndex];
    
    if (!currentAnswer || currentAnswer.trim() === "") {
      setError("Please write something first!");
      return;
    }

    setLoading(true);
    setVideoGenerating(true);
    setError(null);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      
      const response = await fetch(
        `${apiUrl}/api/ai/generate_feedback`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question: questions[currentIndex],
            answer: currentAnswer,
            level: examLevel,
            use_video: true, // Enable D-ID video generation
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to get feedback");
      }

      const data = await response.json();
      
      // Store feedback and video URL
      setFeedback({ ...feedback, [currentIndex]: data.feedback });
      
      if (data.video_url) {
        setVideoUrls({ ...videoUrls, [currentIndex]: data.video_url });
      }
      
      if (!data.has_video) {
        setVideoGenerating(false);
      }
      
    } catch (err) {
      console.error("Feedback Error:", err);
      setError(err.message || "Could not reach the server. Please try again.");
      setFeedback({ 
        ...feedback, 
        [currentIndex]: "Error generating feedback. Please try again." 
      });
    } finally {
      setLoading(false);
    }
  };

  if (questions.length === 0) {
    return (
      <div className="min-h-screen bg-slate-900 text-white p-20 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500 mx-auto mb-4"></div>
          <p>Loading exam...</p>
        </div>
      </div>
    );
  }

  const currentHasFeedback = !!feedback[currentIndex];
  const currentVideoUrl = videoUrls[currentIndex];

  return (
    <div className="min-h-screen bg-slate-900 text-white p-4 sm:p-12 flex flex-col items-center">
      {/* Progress Bar */}
      <div className="w-full max-w-2xl mb-8">
        <div className="flex justify-between mb-2 text-sm text-slate-400">
          <span>{examLevel.toUpperCase()} LEVEL</span>
          <span>{currentIndex + 1} of {questions.length}</span>
        </div>
        <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500 transition-all duration-500"
            style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }}
          ></div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="w-full max-w-2xl mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-300 text-sm">
          {error}
        </div>
      )}

      <div className="w-full max-w-2xl bg-slate-800 border border-white/10 rounded-3xl p-8 shadow-2xl">
        {/* Question */}
        <div className="mb-6">
          <span className="text-emerald-400 font-bold text-sm uppercase tracking-widest">
            Question {currentIndex + 1}
          </span>
          <p className="text-xl font-serif mt-2">{questions[currentIndex]}</p>
        </div>

        {/* Answer TextArea */}
        <textarea
          disabled={currentHasFeedback || loading}
          className="w-full bg-slate-900/50 border-2 border-white/5 rounded-2xl p-5 focus:border-emerald-500 outline-none transition-all min-h-[150px] disabled:opacity-50 text-white placeholder-slate-500"
          placeholder="Type your answer here..."
          value={answers[currentIndex] || ""}
          onChange={(e) => handleUpdateAnswer(e.target.value)}
        />

        {/* Video Feedback Display */}
        {currentHasFeedback && (
          <div className="mt-6 space-y-4 animate-in fade-in slide-in-from-bottom-2">
            
            {/* Video Player (if available) */}
            {currentVideoUrl && (
              <div className="bg-black/30 border border-emerald-500/30 rounded-2xl p-6 overflow-hidden">
                <h4 className="text-emerald-400 font-bold mb-4">Your Teacher (Avatar Video):</h4>
                <video
                  controls
                  className="w-full rounded-lg bg-black aspect-video"
                  src={currentVideoUrl}
                >
                  Your browser does not support the video tag.
                </video>
              </div>
            )}

            {/* Text Feedback */}
            <div className="p-5 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl">
              <h4 className="text-emerald-400 font-bold mb-4">Teacher Feedback:</h4>
              <div className="flex gap-4 items-start">
                {/* Avatar Placeholder */}
                {!currentVideoUrl && (
                  <img
                    src="https://www.clipartmax.com/png/middle/239-2395177_2d-avatar-avatar-2d.png"
                    alt="teacher avatar"
                    className="w-16 h-16 object-cover rounded-full flex-shrink-0"
                  />
                )}
                {/* Feedback Text */}
                <p className="text-slate-300 leading-relaxed text-sm whitespace-pre-wrap flex-1">
                  {feedback[currentIndex]}
                </p>
              </div>
            </div>

            {/* Loading Indicator for Video */}
            {videoGenerating && !currentVideoUrl && (
              <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl text-blue-300 text-sm flex items-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b border-blue-400"></div>
                <span>Avatar video is being generated... (usually takes 15-45 seconds)</span>
              </div>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-4 mt-8">
          {!currentHasFeedback ? (
            <button
              onClick={submitForFeedback}
              disabled={loading || !answers[currentIndex]}
              className="flex-1 py-4 bg-emerald-500 text-slate-900 rounded-xl font-black hover:bg-emerald-400 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="animate-spin inline-block w-4 h-4 border-2 border-slate-900 border-t-transparent rounded-full"></span>
                  Analyzing Answer...
                </span>
              ) : (
                "Check My Answer"
              )}
            </button>
          ) : (
            <button
              onClick={() => {
                if (currentIndex < questions.length - 1) {
                  setCurrentIndex((prev) => prev + 1);
                  // Clear error when moving to next question
                  setError(null);
                } else {
                  router.push("/complete");
                }
              }}
              className="flex-1 py-4 bg-white/10 hover:bg-white/20 rounded-xl font-bold transition"
            >
              {currentIndex === questions.length - 1 ? (
                "Finish Exam →"
              ) : (
                "Next Question →"
              )}
            </button>
          )}
        </div>
      </div>

      {/* Info Footer */}
      <div className="w-full max-w-2xl mt-8 text-center text-xs text-slate-500">
        <p>
          {currentVideoUrl 
            ? "💡 Tip: The video feedback is generated by an AI avatar. You can replay it anytime."
            : "💡 Tip: Submit your answer to get personalized feedback from your teacher."}
        </p>
      </div>
    </div>
  );
}
