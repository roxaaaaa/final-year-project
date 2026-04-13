/** Serialise the exam object stored under `currentExam` when entering practice mode. */
export function serialisePracticeExam(topic, level, questions) {
  return JSON.stringify({ topic, level, questions });
}

/** Serialise autosaved exam payload (includes timestamp). */
export function serialiseAutosavedExam(topic, level, questions, generatedAt) {
  return JSON.stringify({ topic, level, questions, generatedAt });
}
