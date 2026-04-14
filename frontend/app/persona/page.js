"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

export default function PersonaSelection() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const selectPersona = async (persona) => {
    setLoading(true);
    setError("");
    const token = localStorage.getItem("token");
    
    if (!token) {
      router.push("/");
      return;
    }

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/user/persona`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ persona })
      });

      if (!res.ok) {
        throw new Error("Failed to set persona");
      }
      
      router.push("/");
    } catch (err) {
      setError(err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center p-6 relative overflow-hidden">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-emerald-500/20 rounded-full blur-3xl animate-pulse"></div>
      </div>
      
      <div className="relative z-10 max-w-lg w-full text-center">
        <h1 className="text-4xl font-black text-white mb-4">Welcome to AgriExamAI</h1>
        <p className="text-slate-300 text-lg mb-10">How will you be using this platform?</p>
        
        {error && <p className="text-red-400 mb-6 font-medium">{error}</p>}
        {loading && <p className="text-emerald-400 mb-6 font-bold animate-pulse">Setting your persona...</p>}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <button 
            onClick={() => selectPersona('student')}
            disabled={loading}
            className="flex flex-col items-center p-8 bg-slate-800/80 border-2 border-white/10 hover:border-emerald-400 rounded-3xl transition-all hover:scale-105 shadow-xl"
          >
            <div className="text-5xl mb-4">🎓</div>
            <h2 className="text-xl font-bold text-white mb-2">I am a Student</h2>
            <p className="text-slate-400 text-sm">Practice and test my knowledge</p>
          </button>
          
          <button 
            onClick={() => selectPersona('teacher')}
            disabled={loading}
            className="flex flex-col items-center p-8 bg-slate-800/80 border-2 border-white/10 hover:border-teal-400 rounded-3xl transition-all hover:scale-105 shadow-xl"
          >
            <div className="text-5xl mb-4">👨‍🏫</div>
            <h2 className="text-xl font-bold text-white mb-2">I am a Teacher</h2>
            <p className="text-slate-400 text-sm">Create and print exam papers</p>
          </button>
        </div>
      </div>
    </div>
  );
}
