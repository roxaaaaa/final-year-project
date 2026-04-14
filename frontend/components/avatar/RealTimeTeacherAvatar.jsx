"use client";

import { useCallback, useEffect, useState } from "react";
import { TalkingAvatarCanvas } from "./TalkingAvatarCanvas";
import { primeAvatarAudioFromUserGesture, useAvatarAudio } from "./useAvatarAudio";

/**
 * Orchestrates modular pieces: TTS (`useAvatarAudio`) + animation (`TalkingAvatarCanvas`).
 * Starts playback when `feedbackText` changes; offers explicit replay (helps after autoplay restrictions).
 */
export function RealTimeTeacherAvatar({ feedbackText, apiUrl, getToken }) {
  const { speak, amplitude, isSpeaking, ttsError, setTtsError } = useAvatarAudio(apiUrl, getToken);
  const [autoStarted, setAutoStarted] = useState(false);

  const runSpeak = useCallback(async () => {
    if (!feedbackText?.trim()) return;
    try {
      await speak(feedbackText);
    } catch (e) {
      console.error(e);
      setTtsError(e?.message || "Voice playback failed");
    }
  }, [feedbackText, speak, setTtsError]);

  useEffect(() => {
    if (!feedbackText?.trim()) return undefined;
    let cancelled = false;
    (async () => {
      try {
        await runSpeak();
        if (!cancelled) setAutoStarted(true);
      } catch {
        if (!cancelled) setAutoStarted(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [feedbackText, runSpeak]);

  return (
    <div className="rounded-2xl border border-emerald-500/30 bg-black/30 p-4">
      <h4 className="mb-3 text-center text-sm font-bold text-emerald-400">Your teacher (live avatar)</h4>
      <TalkingAvatarCanvas amplitude={amplitude} isSpeaking={isSpeaking} />
      <div className="mt-3 flex flex-col items-center gap-2">
        <button
          type="button"
          onClick={() => {
            primeAvatarAudioFromUserGesture();
            void runSpeak();
          }}
          className="rounded-lg bg-emerald-600/90 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-emerald-500"
        >
          Replay voice
        </button>
        {ttsError && <p className="text-center text-xs text-red-300">{ttsError}</p>}
        {!autoStarted && !ttsError && (
          <p className="text-center text-xs text-slate-500">If you hear nothing, tap Replay (browser audio rules).</p>
        )}
      </div>
    </div>
  );
}
