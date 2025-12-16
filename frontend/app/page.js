"use client";
import { useState, useRef, useEffect } from "react";

export default function Home() {
  const [topic, setTopic] = useState("");
  const [level, setLevel] = useState("higher");
  const [questions, setQuestions] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [loadingText, setLoadingText] = useState("");
  const [focusedInput, setFocusedInput] = useState(false);

  const resultRef = useRef(null);

  const loadingMessages = [
    "Analyzing past exam trends...",
    "Matching question difficulty...",
    "Formatting exam paper...",
  ];

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

    setLoading(true);
    setError("");
    setQuestions("");

    try {
      const response = await fetch("http://localhost:8000/api/ai/generate_questions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          topic_name: topic,
          level: level,
          paper: "",
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to generate questions");
      }

      const data = await response.json();
      setQuestions(data.questions);

      setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 200);
    } catch (err) {
      setError("Unable to generate questions. Please ensure the backend is running.");
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
                        className={`relative p-6 rounded-2xl border-2 transition-all duration-300 text-left overflow-hidden group/btn ${level === l.value
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
                      className="relative w-full px-6 py-5 bg-slate-800/50 border-2 border-white/10 rounded-2xl focus:border-emerald-400 focus:bg-slate-800/80 text-white text-lg placeholder-slate-500 transition-all outline-none"
                      placeholder="e.g., Grassland Management, Dairy Production..."
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
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
                  <p className="text-sm text-slate-400 mt-3">Be specific for best results</p>
                </div>

                {error && (
                  <div className="relative overflow-hidden p-5 bg-red-500/10 border-l-4 border-red-500 rounded-r-xl backdrop-blur-sm">
                    <p className="text-red-200 font-medium text-sm">{error}</p>
                  </div>
                )}

                <button
                  onClick={handleGenerate}
                  disabled={loading || !topic}
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

        {/* Results Section */}
        {questions && (
          <div ref={resultRef} className="animate-fade-in">
            <div className="relative group mb-8">
              <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-3xl blur-2xl opacity-20 group-hover:opacity-30 transition duration-1000"></div>

              <div className="relative bg-slate-800/50 backdrop-blur-xl rounded-3xl border border-white/10 overflow-hidden shadow-2xl">
                <div className="relative bg-gradient-to-r from-emerald-500 to-teal-500 px-8 py-8">
                  <div className="absolute inset-0 bg-black/10"></div>
                  <div className="relative flex items-center justify-between flex-wrap gap-4">
                    <div>
                      <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center font-black text-white text-lg">
                          2
                        </div>
                        <h3 className="text-2xl font-black text-white">Your Exam Paper</h3>
                      </div>
                      <p className="text-emerald-50/80 text-sm ml-13">Ready to practice or print</p>
                    </div>
                    <button
                      onClick={handlePrint}
                      className="flex items-center gap-2 px-6 py-3 bg-white hover:bg-emerald-50 text-emerald-600 rounded-xl font-bold transition-all shadow-lg hover:shadow-xl hover:scale-105"
                    >
                      <span>Print Paper</span>
                    </button>
                  </div>
                </div>

                <div id="exam-paper" className="p-10 sm:p-16 bg-white" style={{ fontFamily: "'Times New Roman', Georgia, serif" }}>
                  <div className="text-center border-b-4 border-slate-900 pb-8 mb-10">
                    <h2 className="text-4xl font-bold uppercase tracking-wider text-slate-900 mb-4">
                      Leaving Certificate Examination
                    </h2>
                    <h3 className="text-2xl font-bold text-slate-800 mb-3">
                      Agricultural Science — {level.toUpperCase()} LEVEL
                    </h3>
                    <p className="italic text-slate-600 text-xl mb-6">Topic: {topic}</p>
                    <div className="inline-block border-4 border-slate-900 px-8 py-3 font-bold text-lg">
                      Total Marks: 60
                    </div>
                  </div>

                  <p className="font-bold uppercase mb-8 text-xl tracking-widest">Section A</p>

                  <div className="whitespace-pre-wrap leading-loose text-slate-900 text-lg">
                    {questions}
                  </div>

                  <div className="mt-20 pt-8 border-t-2 border-slate-200 text-center text-xs text-slate-400">
                    Generated using AI based on past examination patterns
                  </div>
                </div>
              </div>
            </div>

            <button
              onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
              className="w-full py-5 bg-slate-800/50 hover:bg-slate-800/80 backdrop-blur-sm border border-white/10 text-white rounded-2xl font-bold transition-all hover:scale-[1.02]"
            >
              Create Another Exam Paper
            </button>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="relative mt-20 py-10 border-t border-white/10 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6 text-center">
          <p className="text-slate-400 text-sm">
            Designed for Leaving Certificate Agricultural Science students
          </p>
          <p className="text-slate-500 text-xs mt-2">
            © 2024 AgriExamAI • All rights reserved
          </p>
        </div>
      </footer>
    </div>
  );
}