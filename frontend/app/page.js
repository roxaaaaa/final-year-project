"use client";
import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation"; //handling navigation
import { serialiseAutosavedExam, serialisePracticeExam } from "../lib/examStorage";
import { computeGenerationsFromMeResponse } from "../lib/generationLimits";
import { downloadExamExport } from "../lib/downloadExamExport";

export default function Home() {
  const [user, setUser] = useState(null);
  const [generatedId, setGeneratedId] = useState(null);
  const [topic, setTopic] = useState("General Knowledge");
  const [level, setLevel] = useState("ordinary");
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [loadingText, setLoadingText] = useState("");
  const [focusedInput, setFocusedInput] = useState(false);
  const [generationsRemaining, setGenerationsRemaining] = useState(null);
  const [generationsTotal, setGenerationsTotal] = useState(null);
  const [exportError, setExportError] = useState("");
  const [exporting, setExporting] = useState(false);

  const userInitial = user?.name?.charAt(0) ?? "U";
  const userName = user?.name ?? "User";
  const generationsUsed =
    generationsTotal != null && generationsRemaining != null
      ? generationsTotal - generationsRemaining
      : null;

  const resultRef = useRef(null);
  const router = useRouter();

const handlePracticeMode = (practiceId = null, practiceQuestions = null) => {
  const idToUse = practiceId ?? generatedId;
  if (idToUse == null || idToUse === "") {
    console.error("Practice mode requires a saved exam id from the server.");
    return;
  }
  const questionsToSave = practiceQuestions || questions || [];

  localStorage.setItem("currentExam", serialisePracticeExam(topic, level, questionsToSave));

  setGeneratedId(idToUse);
  router.push(`/practice/${idToUse}`);
};

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/user/me`, {
        headers: { "Authorization": `Bearer ${token}` }
      })
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        const { user, generationsTotal, generationsRemaining } = computeGenerationsFromMeResponse(data);
        if (!user) {
          localStorage.removeItem("token");
          return;
        }
        setUser(user);
        setGenerationsTotal(generationsTotal);
        setGenerationsRemaining(generationsRemaining);
      })
      .catch(() => {});
    }
  }, []);

  const loadingMessages = [
    "Analyzing past exam papers...",
    "Looking for question patterns...",
    "Matching question difficulty...",
    "Formatting exam paper...",
    "Pls be patient..."
  ];

  useEffect(() => {
    if (questions) {
      const generatedAt = new Date().toISOString();
      localStorage.setItem(
        "currentExam",
        serialiseAutosavedExam(topic, level, questions, generatedAt)
      );
    }
  }, [questions, topic, level]); 

  useEffect(() => {
    if (!loading) return;
    let i = 0;
    setLoadingText(loadingMessages[0]);
    const interval = setInterval(() => {
      i = (i + 1) % loadingMessages.length;
      setLoadingText(loadingMessages[i]);
    }, 1200);
    return () => clearInterval(interval);
  }, [loading]);

  const handleGenerate = async () => {
    if (!topic) return;

    if (!user) {
      window.location.href = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/auth/google?redirect_to=/`;
      return;
    }

    setLoading(true);
    setError("");
    setExportError("");
    setQuestions("");

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/ai/generate_questions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("token")}`
        },
        body: JSON.stringify({
          topic_name: topic,
          level: level,
          paper: "",
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to generate questions");
      }

      const data = await response.json();
      const examId = data.exam_id;
      setQuestions(data.questions);
      setGeneratedId(examId);
      
      // Update generations remaining from response
      if (data.generations_remaining !== undefined) {
        setGenerationsRemaining(data.generations_remaining);
      }

      // Auto-redirect students to practice mode after generation
      if (user?.persona === 'student') {
        setLoadingText("Redirecting to practice mode...");
        setTimeout(() => {
          handlePracticeMode(examId, data.questions);
        }, 1000); // Brief delay to show success
      } else {
        // For teachers, scroll to show the generated paper
        setTimeout(() => {
          resultRef.current?.scrollIntoView({ behavior: "smooth" });
        }, 200);
      }
    } catch (err) {
      setError(err.message || "Unable to generate questions.");
    } finally {
      setLoading(false);
    }
  };

  const handlePrint = () => {
    const content = document.getElementById("exam-paper").innerHTML;
    const original = document.body.innerHTML;
    document.body.innerHTML = content;
    window.print();
    document.body.innerHTML = original;
    window.location.reload();
  };

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const handleDownloadExam = async (format) => {
    const token = localStorage.getItem("token");
    if (!generatedId) {
      setExportError("No exam to download yet.");
      return;
    }
    setExportError("");
    setExporting(true);
    try {
      const result = await downloadExamExport(apiBase, generatedId, format, token);
      if (!result.ok) {
        setExportError(result.message || "Download failed.");
      }
    } catch (e) {
      setExportError(e.message || "Download failed.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-emerald-900 to-slate-900 relative overflow-hidden">
      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl animate-float"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '1s' }}></div>
        <div className="absolute top-1/2 left-1/2 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl animate-float" style={{ animationDelay: '2s' }}></div>
      </div>

      {/* Glass Header */}
      <header className="relative border-b border-white/10 backdrop-blur-xl bg-white/5 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-emerald-400 to-teal-400 rounded-2xl blur opacity-75"></div>
                <div className="relative w-12 h-12 bg-gradient-to-br from-emerald-400 to-teal-500 rounded-2xl flex items-center justify-center shadow-xl">
                  <div className="text-white font-black text-xl">AG</div>
                </div>
              </div>
              <div>
                <h1 className="text-2xl font-black text-white tracking-tight">AgriExam<span className="text-emerald-400">AI</span></h1>
                <p className="text-xs text-emerald-300/80 font-medium">Leaving Cert Generator</p>
              </div>
            </div>
            <div>
              {user ? (
                <div className="flex items-center gap-3 bg-slate-800/80 px-4 py-2 rounded-full border border-white/10">
                  <div className="w-8 h-8 bg-emerald-500 rounded-full flex items-center justify-center font-bold text-white uppercase">{userInitial}</div>
                  <span className="text-white text-sm font-medium">{userName}</span>
                  {user.persona && <span className="text-xs bg-emerald-900 text-emerald-300 px-2 py-0.5 rounded-full">{user.persona}</span>}
                  {generationsUsed !== null && (
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-bold whitespace-nowrap ${
                        generationsRemaining === 0 ? "bg-red-900 text-red-300" : "bg-blue-900 text-blue-300"
                      }`}
                    >
                      {generationsUsed}/{generationsTotal} attempts
                    </span>
                  )}
                  <button onClick={() => { localStorage.removeItem("token"); window.location.reload(); }} className="text-xs text-slate-400 hover:text-white ml-2 rounded">Logout</button>
                </div>
              ) : (
                <button onClick={() => window.location.href = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/auth/google?redirect_to=/`} className="bg-white text-slate-900 px-5 py-2.5 rounded-xl font-bold flex items-center gap-2 hover:bg-slate-100 transition-colors shadow-lg">
                  <svg className="w-5 h-5" viewBox="0 0 24 24"><path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
                  Sign in with Google
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="relative max-w-6xl mx-auto px-6 py-12 sm:py-20">
        {/* Hero Section */}
        <div className="text-center mb-16 sm:mb-20">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-emerald-500/20 to-teal-500/20 border border-emerald-400/30 backdrop-blur-sm mb-6">
            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
            <span className="text-sm font-bold text-emerald-300">AI-Powered Exam Practice</span>
          </div>

          <h2 className="text-5xl sm:text-7xl font-black text-white mb-6 leading-tight tracking-tight">
            Master Your
            <br />
            <span className="bg-gradient-to-r from-emerald-400 via-teal-400 to-cyan-400 bg-clip-text text-transparent">
              Leaving Cert
            </span>
          </h2>

          <p className="text-xl text-slate-300 max-w-2xl mx-auto leading-relaxed">
            Generate authentic Agricultural Science exam questions instantly.
            <span className="text-emerald-400 font-semibold"> Practice smarter, not harder.</span>
          </p>
        </div>

        {/* Main Card */}
        <div className="relative group mb-12">
          {/* Glow effect */}
          <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-3xl blur-2xl opacity-20 group-hover:opacity-30 transition duration-1000"></div>

          <div className="relative bg-slate-800/50 backdrop-blur-xl rounded-3xl border border-white/10 overflow-hidden shadow-2xl">
            {/* Limit Reached Notification */}
            {user &&
              (user.persona === "teacher" || user.persona === "student") &&
              generationsRemaining === 0 && (
              <div className="bg-red-900/30 border-b border-red-500/30 px-8 py-4">
                <div className="flex items-center gap-3">
                  <div className="w-6 h-6 bg-red-500 rounded-full flex items-center justify-center flex-shrink-0">
                    <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M12 9v2m0 4v2m0-10a8 8 0 110 16 8 8 0 010-16z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-red-300 font-bold text-sm">
                      Generation limit reached
                    </p>
                    <p className="text-red-200/80 text-xs mt-0.5">
                      You have used all {generationsTotal ?? ""} exam generations allowed for your account. Thank you for using AgriExamAI!
                    </p>
                  </div>
                </div>
              </div>
            )}
            
            {/* Card Header */}
            <div className="relative bg-gradient-to-r from-emerald-500 to-teal-500 px-8 py-8">
              <div className="absolute inset-0 bg-black/10"></div>
              <div className="relative">
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center font-black text-white text-lg">
                    1
                  </div>
                  <h3 className="text-2xl font-black text-white">Configure Your Exam</h3>
                </div>
                <p className="text-emerald-50/80 text-sm ml-13">Select your level and topic</p>
              </div>
            </div>

            <div className="p-8 sm:p-10">
              <div className="space-y-8">
                {/* Level Selection */}
                <div>
                  <label className="block text-sm font-bold text-white/90 mb-5 uppercase tracking-wider">Exam Level</label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                    {[
                      { value: "higher", title: "Higher Level", desc: "Complex analysis & critical thinking" },
                      { value: "ordinary", title: "Ordinary Level", desc: "Core concepts & understanding" }
                    ].map((l) => (
                      <button
                        key={l.value}
                        type="button"
                        onClick={() => setLevel(l.value)}
                        disabled={loading}
                        className={`relative p-6 rounded-2xl border-2 transition-all duration-300 text-left overflow-hidden group/btn ${loading ? 'opacity-50 cursor-not-allowed' : ''} ${level === l.value
                          ? "border-emerald-400 bg-gradient-to-br from-emerald-500/20 to-teal-500/20 shadow-xl shadow-emerald-500/20 scale-[1.02]"
                          : "border-white/10 bg-slate-800/50 hover:border-emerald-400/50 hover:bg-slate-800/80"
                          }`}
                      >
                        {level === l.value && (
                          <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/10 to-teal-500/10 shimmer"></div>
                        )}
                        <div className="relative">
                          <div className="flex items-center justify-between mb-4">
                            <div className={`text-2xl font-black tracking-tight ${level === l.value ? "text-emerald-400" : "text-white/40"
                              }`}>
                              {l.value === "higher" ? "H" : "O"}
                            </div>
                            <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${level === l.value ? "border-emerald-400 bg-emerald-400 scale-110" : "border-white/30"
                              }`}>
                              {level === l.value && (
                                <div className="w-2 h-2 bg-white rounded-full"></div>
                              )}
                            </div>
                          </div>
                          <p className="font-black text-xl text-white mb-2">{l.title}</p>
                          <p className="text-sm text-slate-400">{l.desc}</p>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Topic Input */}
                <div>
                  <label className="block text-sm font-bold text-white/90 mb-4 uppercase tracking-wider">Exam Topic</label>
                  <div className="relative group">
                    <div className={`absolute -inset-0.5 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-2xl blur opacity-0 group-hover:opacity-20 transition duration-300 ${focusedInput ? 'opacity-30' : ''}`}></div>
                    <input
                      type="text"
                      className={`relative w-full px-6 py-5 bg-slate-800/50 border-2 border-white/10 rounded-2xl focus:border-emerald-400 focus:bg-slate-800/80 text-white text-lg placeholder-slate-500 transition-all outline-none ${loading ? 'opacity-50 cursor-not-allowed disabled:bg-slate-800/30' : ''}`}
                      placeholder="General Knowledge ..."
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      disabled={loading}
                      onFocus={() => setFocusedInput(true)}
                      onBlur={() => setFocusedInput(false)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !loading && topic) {
                          handleGenerate();
                        }
                      }}
                    />
                    {topic && (
                      <div className="absolute right-5 top-1/2 -translate-y-1/2">
                        <div className="w-8 h-8 bg-emerald-500 rounded-full flex items-center justify-center animate-pulse">
                          <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full"></div>
                        </div>
                      </div>
                    )}
                  </div>
                  <p className="text-sm text-slate-400 mt-3"> You can be more specific and change it</p>
                </div>

                {error && (
                  <div className="relative overflow-hidden p-5 bg-red-500/10 border-l-4 border-red-500 rounded-r-xl backdrop-blur-sm">
                    <p className="text-red-200 font-medium text-sm">{error}</p>
                  </div>
                )}

                <button
                  onClick={handleGenerate}
                  disabled={
                    loading ||
                    !topic ||
                    (generationsRemaining !== null &&
                      generationsRemaining === 0 &&
                      (user?.persona === "teacher" || user?.persona === "student"))
                  }
                  title={
                    generationsRemaining === 0 &&
                    (user?.persona === "teacher" || user?.persona === "student")
                      ? "You have reached your generation limit"
                      : ""
                  }
                  className="relative w-full group/btn overflow-hidden rounded-2xl disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-emerald-500 to-teal-500 transition-transform group-hover/btn:scale-105"></div>
                  <div className="absolute inset-0 bg-gradient-to-r from-emerald-400 to-teal-400 opacity-0 group-hover/btn:opacity-100 transition-opacity"></div>
                  {loading && <div className="absolute inset-0 shimmer"></div>}

                  <div className="relative px-8 py-5 flex items-center justify-center gap-3">
                    {loading ? (
                      <>
                        <div className="w-6 h-6 border-3 border-white/30 border-t-white rounded-full animate-spin"></div>
                        <span className="font-bold text-white text-lg">{loadingText}</span>
                      </>
                    ) : (
                      <>
                        <span className="font-black text-white text-lg tracking-wide">Generate Exam Questions</span>
                        <span className="text-white text-xl group-hover/btn:translate-x-1 transition-transform">→</span>
                      </>
                    )}
                  </div>
                </button>

                <div className="flex items-center justify-center gap-8 text-xs text-slate-400 flex-wrap pt-2">
                  {['Authentic Format', 'Instant Generation', 'Print Ready'].map((feature) => (
                    <div key={feature} className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full"></div>
                      <span className="font-medium">{feature}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Results Section - Only show for teachers */}
        {questions && user?.persona === 'teacher' && (
        <div ref={resultRef} className="animate-fade-in">
          <div className="relative group mb-8">
            <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-3xl blur-2xl opacity-20 group-hover:opacity-30 transition duration-1000"></div>
            <div className="relative bg-slate-800/50 backdrop-blur-xl rounded-3xl border border-white/10 overflow-hidden shadow-2xl">
              <div className="relative bg-gradient-to-r from-emerald-500 to-teal-500 px-8 py-8">
                <div className="absolute inset-0 bg-black/10"></div>
                <div className="relative flex flex-col sm:flex-row items-center justify-between gap-6">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center font-black text-white text-lg">
                      2
                    </div>
                    <div>
                      <h3 className="text-2xl font-black text-white">Paper Generated!</h3>
                      <p className="text-emerald-50/80 text-sm">Choose how you want to proceed</p>
                    </div>
                  </div>
                  
                  <div className="flex w-full flex-col items-center gap-2 sm:w-auto sm:items-end">
                    <div className="flex flex-col items-center gap-3 sm:flex-row sm:flex-wrap sm:justify-end">
                      {user?.persona === "teacher" && (
                        <>
                          <button
                            type="button"
                            onClick={() => handleDownloadExam("pdf")}
                            disabled={exporting}
                            className="flex items-center gap-2 px-5 py-3 bg-white/15 hover:bg-white/25 text-white border border-white/25 rounded-xl font-bold transition-all backdrop-blur-md disabled:opacity-50"
                          >
                            {exporting ? "…" : "Download PDF"}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDownloadExam("docx")}
                            disabled={exporting}
                            className="flex items-center gap-2 px-5 py-3 bg-white/15 hover:bg-white/25 text-white border border-white/25 rounded-xl font-bold transition-all backdrop-blur-md disabled:opacity-50"
                          >
                            {exporting ? "…" : "Download Word"}
                          </button>
                          <button
                            type="button"
                            onClick={handlePrint}
                            className="flex items-center gap-2 px-6 py-3 bg-white/10 hover:bg-white/20 text-white border border-white/20 rounded-xl font-bold transition-all backdrop-blur-md"
                          >
                            <span>Print</span>
                            <span className="text-lg" aria-hidden>
                              🖨️
                            </span>
                          </button>
                        </>
                      )}
                    </div>
                    {exportError ? (
                      <p className="max-w-md text-center text-sm text-amber-200 sm:text-right">{exportError}</p>
                    ) : null}
                  </div>
                </div>
              </div>

              {/* Preview of the paper remains below */}
              <div className="max-h-[500px] overflow-y-auto bg-white">
                  <div id="exam-paper" className="p-10 sm:p-16" style={{ fontFamily: "'Times New Roman', Georgia, serif" }}>
                    <div className="text-center border-b-4 border-slate-900 pb-8 mb-10">
                      <h2 className="text-4xl font-bold uppercase tracking-wider text-slate-900 mb-4">Leaving Certificate Practice</h2>
                      <h3 className="text-2xl font-bold text-slate-800 mt-4">Agricultural Science — {level.charAt(0).toUpperCase() + level.slice(1)}</h3>
                    </div>
                    <div className="text-slate-900 text-lg leading-relaxed">
                      {Array.isArray(questions) ? questions.map((q, idx) => (
                        <div key={idx} className="mb-6">
                          <p><strong>{idx + 1}.</strong> {q}</p>
                        </div>
                      )) : questions}
                    </div>
                  </div>
              </div>
            </div>
          </div>
        </div>
      )}
      </main>

      {/* Footer */}
      <footer className="relative mt-20 py-10 border-t border-white/10 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6 text-center">
          <p className="text-slate-400 text-sm">
            Disclaimer: This tool is intended for revision purposes and is designed to supplement, not replace, official curriculum materials provided by the SEC.
          </p>
          <p className="text-slate-500 text-xs mt-2">
            © 2025 AgriExamAI • All rights reserved
          </p>
        </div>
      </footer>
    </div>
  );
}