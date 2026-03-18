"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

export default function FeedbackPage() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [aiFeedback, setAiFeedback] = useState([]);
  const router = useRouter();

  useEffect(() => {
    const savedExam = localStorage.getItem("currentExam");
    const savedAnswers = localStorage.getItem("practice_progress");

    if (savedExam && savedAnswers) {
      const examData = JSON.parse(savedExam);
      const answersData = JSON.parse(savedAnswers);
      
      setResults({
        questions: examData.questions,
        answers: answersData
      });
      
      fetchFeedback(examData.questions, answersData);
    } else {
      router.push("/");
    }
  }, []);

  const fetchFeedback = async (questions, answers) => {
    setLoading(true);
    try {
      // Calling FastAPI endpoint
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/ai/generate_feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ questions, answers }),
      });
      const data = await response.json();
      setAiFeedback(data.feedback_reports);
    } catch (error) {
      console.error("Failed to fetch feedback:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="p-10 text-center">Examiner is reviewing your work...</div>;

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Exam Feedback</h1>
      
      {results?.questions.map((q, index) => (
        <div key={index} className="mb-8 p-6 border rounded-lg bg-white shadow-sm">
          <h2 className="font-semibold text-lg text-green-800">Question {index + 1}</h2>
          <p className="italic mb-4">"{q}"</p>
          
          <div className="bg-gray-50 p-4 rounded mb-4">
            <span className="text-sm font-bold text-gray-500 uppercase">Your Answer:</span>
            <p className="mt-1">{results.answers[index] || "No answer provided."}</p>
          </div>

          <div className="border-t pt-4">
            <span className="text-sm font-bold text-blue-600 uppercase">Examiner Feedback:</span>
            <p className="mt-2 text-gray-800">
            {aiFeedback && aiFeedback[index] ? aiFeedback[index].feedback : "Loading feedback..."}
            </p>
            <div className="mt-2 text-sm font-medium text-green-700">
            Grade: {aiFeedback && aiFeedback[index] ? aiFeedback[index].score : "..."}
            </div>
          </div>
        </div>
      ))}

      <button 
        onClick={() => router.push("/")}
        className="w-full py-3 bg-green-600 text-white rounded-lg font-bold hover:bg-green-700"
      >
        Start New Topic
      </button>
    </div>
  );
}