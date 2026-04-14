"use client";
export default function Thanks() {
  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-6 text-white text-center">
      <div className="max-w-xl w-full bg-slate-800 rounded-3xl p-12 border border-white/10 shadow-xl">
        <div className="text-6xl mb-6">🎉</div>
        <h1 className="text-3xl font-black text-emerald-400 mb-6">Thank You!</h1>
        <p className="text-slate-300 text-lg leading-relaxed mb-10">
          Thank you for taking part in my dissertation testing, I really appreciate it. Now you can come back to the MS Form and tell me about your experience.
        </p>
        <button 
          onClick={() => window.location.href = "/"}
          className="bg-white/10 hover:bg-white/20 text-white font-bold py-3 px-8 rounded-xl border border-white/20 transition-colors inline-block"
        >
          Return Home
        </button>
      </div>
    </div>
  );
}
