"use client";

/**
 * Browser Web Speech (`speechSynthesis`) with a synthetic 0–1 amplitude for simple lip sync.
 * No server TTS: no API URL, tokens, or MP3 decode.
 */

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Call from the same user click as replay/autoplay paths so strict browsers are more likely
 * to allow `speechSynthesis` after gesture (behavior varies by browser).
 */
export function primeAvatarAudioFromUserGesture() {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  try {
    window.speechSynthesis.resume();
  } catch {
    /* ignore */
  }
}

/**
 * @returns {{ speak: (text: string) => Promise<void>, amplitude: number, isSpeaking: boolean, ttsError: string|null, setTtsError: (e: string|null) => void }}
 *
 * `speak` uses `SpeechSynthesisUtterance`. `amplitude` is a smoothed sine envelope while
 * an utterance is active (not RMS from audio — Web Speech does not expose that).
 */
export function useAvatarAudio() {
  const [amplitude, setAmplitude] = useState(0);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [ttsError, setTtsError] = useState(null);
  const rafRef = useRef(0);
  const envelopeStartRef = useRef(0);

  const stopEnvelope = useCallback(() => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = 0;
    }
    setAmplitude(0);
  }, []);

  const startEnvelope = useCallback(() => {
    envelopeStartRef.current = performance.now();
    const tick = () => {
      const t = (performance.now() - envelopeStartRef.current) / 1000;
      const wave = 0.35 + 0.4 * (0.5 + 0.5 * Math.sin(t * 14));
      setAmplitude(Math.min(1, wave));
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
  }, []);

  useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      stopEnvelope();
      setIsSpeaking(false);
    };
  }, [stopEnvelope]);

  const speak = useCallback(
    async (text) => {
      setTtsError(null);
      const trimmed = (text || "").trim();
      if (!trimmed) return;

      if (typeof window === "undefined" || !window.speechSynthesis) {
        throw new Error("Speech synthesis is not supported in this browser");
      }

      window.speechSynthesis.cancel();

      await new Promise((resolve, reject) => {
        const utter = new SpeechSynthesisUtterance(trimmed);
        utter.onstart = () => {
          setIsSpeaking(true);
          startEnvelope();
        };
        utter.onend = () => {
          stopEnvelope();
          setIsSpeaking(false);
          resolve();
        };
        utter.onerror = (ev) => {
          stopEnvelope();
          setIsSpeaking(false);
          reject(new Error(ev.error || "Speech synthesis failed"));
        };
        window.speechSynthesis.speak(utter);
      });
    },
    [startEnvelope, stopEnvelope]
  );

  return { speak, amplitude, isSpeaking, ttsError, setTtsError };
}
