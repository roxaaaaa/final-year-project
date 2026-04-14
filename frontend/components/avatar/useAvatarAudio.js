"use client";

import { useCallback, useRef, useState } from "react";

let audioCtxSingleton = null;

function getAudioContext() {
  if (typeof window === "undefined") return null;
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return null;
  if (!audioCtxSingleton) audioCtxSingleton = new AC();
  return audioCtxSingleton;
}

/**
 * Call synchronously from the same user gesture as “Check answer” so browsers allow `decodeAudioData` + playback.
 * The hook reuses this singleton context for all TTS playback.
 */
export function primeAvatarAudioFromUserGesture() {
  const ctx = getAudioContext();
  if (ctx?.state === "suspended") {
    void ctx.resume();
  }
}

/**
 * TTS → Web Audio → amplitude for lip sync
 *
 * - `speak(text)` POSTs to `/api/tts/speak`, decodes MP3, plays via BufferSource, and reads RMS from an AnalyserNode.
 * - `amplitude` (0–1) is a coarse mouth driver (volume envelope). Same hook can later accept a viseme timeline
 *   from a TTS provider or a separate phoneme aligner instead of RMS (see comments in `TalkingAvatarCanvas`).
 */
export function useAvatarAudio(apiUrl, getToken) {
  const [amplitude, setAmplitude] = useState(0);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [ttsError, setTtsError] = useState(null);
  const sourceRef = useRef(null);

  const speak = useCallback(
    async (text) => {
      setTtsError(null);
      const trimmed = (text || "").trim();
      if (!trimmed) return;

      const ctx = getAudioContext();
      if (!ctx) throw new Error("Web Audio API not available");
      if (ctx.state === "suspended") await ctx.resume();

      const token = typeof getToken === "function" ? getToken() : getToken;
      const res = await fetch(`${apiUrl}/api/tts/speak`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text: trimmed }),
      });

      if (!res.ok) {
        let detail = res.statusText;
        try {
          const err = await res.json();
          if (err?.detail) detail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
        } catch {
          /* ignore */
        }
        throw new Error(detail);
      }

      const blob = await res.blob();

      if (sourceRef.current) {
        try {
          sourceRef.current.stop();
        } catch {
          /* already stopped */
        }
      }

      const arrayBuffer = await blob.arrayBuffer();
      const audioBuffer = await ctx.decodeAudioData(arrayBuffer.slice(0));

      const source = ctx.createBufferSource();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 512;
      analyser.smoothingTimeConstant = 0.45;
      source.buffer = audioBuffer;
      source.connect(analyser);
      analyser.connect(ctx.destination);

      const data = new Uint8Array(analyser.fftSize);
      let raf = 0;
      let alive = true;

      const tick = () => {
        if (!alive) return;
        analyser.getByteTimeDomainData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i++) {
          const v = (data[i] - 128) / 128;
          sum += v * v;
        }
        const rms = Math.sqrt(sum / data.length);
        setAmplitude(Math.min(1, rms * 5));
        raf = requestAnimationFrame(tick);
      };

      source.onended = () => {
        alive = false;
        cancelAnimationFrame(raf);
        sourceRef.current = null;
        setIsSpeaking(false);
        setAmplitude(0);
      };

      sourceRef.current = source;
      setIsSpeaking(true);
      tick();
      source.start(0);
    },
    [apiUrl, getToken]
  );

  return { speak, amplitude, isSpeaking, ttsError, setTtsError };
}
