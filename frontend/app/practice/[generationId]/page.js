"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";

export default function PracticePage() {
  const { generationId } = useParams();
  const [questions, setQuestions] = useState([]);
  const [examLevel, setExamLevel] = useState("ordinary");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [feedback, setFeedback] = useState({});
  const [videoUrls, setVideoUrls] = useState({});
  const [videoStatuses, setVideoStatuses] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const router = useRouter();

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Load exam from API on mount
  useEffect(() => {
    const loadExam = async () => {
      try {
        const token = localStorage.getItem("token");
        if (!token) {
          router.push("/");
          return;
        }

        const response = await fetch(`${apiUrl}/api/exams/${generationId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!response.ok) {
          throw new Error("Exam not found");
        }

        const data = await response.json();
        setQuestions(data.questions || []);
        setExamLevel(data.level);

        // Load existing practice attempt and feedback
        await loadExistingData(token);
      } catch (e) {
        console.error("Error loading exam:", e);
        setError("Failed to load exam. Please try again.");
        router.push("/");
      }
    };

    const loadExistingData = async (token) => {
      try {
        const response = await fetch(`${apiUrl}/api/practice/attempt/${generationId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (response.ok) {
          const data = await response.json();
          if (data.answers) {
            setAnswers(
              typeof data.answers === "string" ? JSON.parse(data.answers) : data.answers
            );
          }
          if (data.feedback) {
            const feedbackMap = {};
            const vUrls = {};
            const vStat = {};
            data.feedback.forEach((f) => {
              feedbackMap[f.question_index] = f.feedback_text;
              if (f.video_url) {
                vUrls[f.question_index] = f.video_url;
              }
              if (f.video_status) {
                vStat[f.question_index] = f.video_status;
              }
            });
            setFeedback(feedbackMap);
            setVideoUrls(vUrls);
            setVideoStatuses(vStat);
          }
        }
      } catch (e) {
        // Ignore errors for existing data - it's optional
        console.log("No existing practice data found");
      }
    };

    if (generationId) {
      loadExam();
    }
  }, [generationId, router, apiUrl]);

  const handleUpdateAnswer = (val) => {
    setAnswers({ ...answers, [currentIndex]: val });
    setError(null);
  };

  // Auto-save answers to API
  useEffect(() => {
    const saveAnswers = async () => {
      if (Object.keys(answers).length > 0) {
        const saveUrl = `${apiUrl}/api/practice/start`;
        try {
          const token = localStorage.getItem("token");
          await fetch(saveUrl, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              exam_id: parseInt(generationId, 10),
              answers: answers,
            }),
          });
        } catch (e) {
          console.error("Failed to save answers:", e);
        }
      }
    };

    const timeoutId = setTimeout(saveAnswers, 1000); // Auto-save after 1 second of inactivity
    return () => clearTimeout(timeoutId);
  }, [answers, generationId, apiUrl]);

  const submitForFeedback = async () => {
    const currentAnswer = answers[currentIndex];

    if (!currentAnswer || currentAnswer.trim() === "") {
      setError("Please write something first!");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const token = localStorage.getItem("token");

      const response = await fetch(`${apiUrl}/api/feedback/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          exam_id: parseInt(generationId, 10),
          question_index: currentIndex,
          answer: currentAnswer,
          use_video: true,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to get feedback");
      }

      const data = await response.json();

      setFeedback({ ...feedback, [currentIndex]: data.feedback });
      setVideoStatuses({ ...videoStatuses, [currentIndex]: data.video_status });
      if (data.video_url) {
        setVideoUrls({ ...videoUrls, [currentIndex]: data.video_url });
      } else {
        const next = { ...videoUrls };
        delete next[currentIndex];
        setVideoUrls(next);
      }
    } catch (err) {
      console.error("Feedback Error:", err);
      setError(err.message || "Could not reach the server. Please try again.");
      setFeedback({
        ...feedback,
        [currentIndex]: "Error generating feedback. Please try again.",
      });
    } finally {
      setLoading(false);
    }
  };

  if (questions.length === 0) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-900 p-20 text-white">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-b-2 border-emerald-500"></div>
          <p>Loading exam...</p>
        </div>
      </div>
    );
  }

  const currentHasFeedback = !!feedback[currentIndex];
  const currentVideoUrl = videoUrls[currentIndex];
  const currentVideoStatus = videoStatuses[currentIndex];

  return (
    <div className="flex min-h-screen flex-col items-center bg-slate-900 p-4 text-white sm:p-12">
      {/* Progress Bar */}
      <div className="mb-8 w-full max-w-2xl">
        <div className="mb-2 flex justify-between text-sm text-slate-400">
          <span>{examLevel.toUpperCase()} LEVEL</span>
          <span>
            {currentIndex + 1} of {questions.length}
          </span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full bg-emerald-500 transition-all duration-500"
            style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }}
          ></div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-6 w-full max-w-2xl rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
          {error}
        </div>
      )}

      <div className="w-full max-w-2xl rounded-3xl border border-white/10 bg-slate-800 p-8 shadow-2xl">
        {/* Question */}
        <div className="mb-6">
          <span className="text-sm font-bold uppercase tracking-widest text-emerald-400">Question {currentIndex + 1}</span>
          <p className="mt-2 font-serif text-xl">{questions[currentIndex]}</p>
        </div>

        {/* Answer TextArea */}
        <textarea
          disabled={currentHasFeedback || loading}
          className="min-h-[150px] w-full rounded-2xl border-2 border-white/5 bg-slate-900/50 p-5 text-white outline-none transition-all placeholder:text-slate-500 focus:border-emerald-500 disabled:opacity-50"
          placeholder="Type your answer here..."
          value={answers[currentIndex] || ""}
          onChange={(e) => handleUpdateAnswer(e.target.value)}
        />

        {/* D-ID video + text feedback */}
        {currentHasFeedback && (
          <div className="mt-6 animate-in space-y-4 fade-in slide-in-from-bottom-2">
            <div className="rounded-2xl border border-emerald-500/30 bg-black/30 p-4">
              <h4 className="mb-3 text-center text-sm font-bold text-emerald-400">Your teacher (D-ID)</h4>
              {currentVideoUrl ? (
                <video
                  key={currentVideoUrl}
                  controls
                  playsInline
                  className="mx-auto max-h-[min(360px,50vh)] w-full max-w-lg rounded-lg bg-black"
                  src={currentVideoUrl}
                />
              ) : (
                <p className="text-center text-sm text-slate-400">
                  {currentVideoStatus === "skipped" &&
                    "No video: D-ID is not configured on the server. Text feedback is below."}
                  {currentVideoStatus === "failed" &&
                    "Video could not be generated. Text feedback is below."}
                  {(currentVideoStatus === "not_used" || !currentVideoStatus) &&
                    "No teacher video for this answer. Text feedback is below."}
                </p>
              )}
            </div>

            <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-5">
              <h4 className="mb-4 font-bold text-emerald-400">Teacher Feedback:</h4>
              <p className="text-sm leading-relaxed whitespace-pre-wrap text-slate-300">{feedback[currentIndex]}</p>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="mt-8 flex gap-4">
          {!currentHasFeedback ? (
            <button
              onClick={submitForFeedback}
              disabled={loading || !answers[currentIndex]}
              className="flex-1 rounded-xl bg-emerald-500 py-4 font-black text-slate-900 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-slate-900 border-t-transparent"></span>
                  Generating feedback and video…
                </span>
              ) : (
                "Check My Answer"
              )}
            </button>
          ) : (
            <button
              disabled={loading}
              onClick={async () => {
                if (currentIndex < questions.length - 1) {
                  setCurrentIndex((prev) => prev + 1);
                  setError(null);
                } else {
                  router.push(`/thanks`); // Navigate directly to thanks page
                }
              }}
              className="flex-1 rounded-xl bg-white/10 py-4 font-bold transition hover:bg-white/20"
            >
              {currentIndex === questions.length - 1 ? (loading ? "Submitting..." : "Finish Exam →") : "Next Question →"}
            </button>
          )}
        </div>
      </div>

      {/* Info Footer */}
      <div className="mt-8 w-full max-w-2xl text-center text-xs text-slate-500">
        <p>Tip: After you submit an answer, the teacher may appear as a D-ID video when the server has D-ID configured (this can take up to a minute).</p>
      </div>
    </div>
  );
}
