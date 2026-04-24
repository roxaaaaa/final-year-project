"use client";

/**
 * Simple mouth visual driven by `amplitude` (0–1) and `isSpeaking`.
 * Lip sync is cosmetic (e.g. synthetic envelope from Web Speech), not phoneme-accurate.
 */
export function TalkingAvatarCanvas({ amplitude = 0, isSpeaking = false }) {
  const open = Math.min(1, Math.max(0, amplitude)) * 0.55 + (isSpeaking ? 0.12 : 0);
  const scaleY = 0.35 + open;

  return (
    <div
      className="relative mx-auto flex h-40 w-40 items-center justify-center rounded-full bg-gradient-to-b from-slate-700 to-slate-900 shadow-inner ring-2 ring-emerald-600/40"
      aria-hidden
    >
      <div className="flex flex-col items-center gap-3 pt-2">
        <div className="h-3 w-3 rounded-full bg-slate-900 ring-1 ring-slate-600" />
        <div className="h-3 w-3 rounded-full bg-slate-900 ring-1 ring-slate-600" />
        <div
          className="mt-1 h-5 w-14 rounded-full bg-slate-950 transition-transform duration-75 ease-out"
          style={{ transform: `scaleY(${scaleY})` }}
        />
      </div>
    </div>
  );
}
