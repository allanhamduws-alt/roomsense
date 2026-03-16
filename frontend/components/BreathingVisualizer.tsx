"use client";

import { useEffect, useRef, useState } from "react";

interface BreathingVisualizerProps {
  breathingRate: number | null;
  intensity: number;
}

export default function BreathingVisualizer({
  breathingRate,
  intensity,
}: BreathingVisualizerProps) {
  const [phase, setPhase] = useState(0);
  const animRef = useRef<number>(0);
  const startRef = useRef<number>(Date.now());

  // Derive estimated pulse from breathing rate (x4 approximation)
  const estimatedPulse =
    breathingRate !== null ? Math.round(breathingRate * 4.2) : null;

  // Animate heartbeat based on estimated pulse
  useEffect(() => {
    const bpm = estimatedPulse ?? 68;
    const cycleDurationMs = (60 / bpm) * 1000;

    function animate() {
      const elapsed = Date.now() - startRef.current;
      const raw = (elapsed % cycleDurationMs) / cycleDurationMs;
      // Heartbeat shape: two quick peaks then rest
      let beat: number;
      if (raw < 0.1) {
        // First beat (systole) — sharp rise
        beat = Math.sin((raw / 0.1) * Math.PI);
      } else if (raw < 0.15) {
        // Brief dip
        beat = Math.sin(((raw - 0.1) / 0.05) * Math.PI) * 0.3;
      } else if (raw < 0.25) {
        // Second beat (diastole)
        beat = Math.sin(((raw - 0.15) / 0.1) * Math.PI) * 0.6;
      } else {
        // Rest phase
        beat = 0;
      }
      setPhase(Math.max(0, beat));
      animRef.current = requestAnimationFrame(animate);
    }

    animRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animRef.current);
  }, [estimatedPulse]);

  const scale = 0.9 + phase * 0.15;
  const active = estimatedPulse !== null;
  const heartColor = active ? "239, 68, 68" : "115, 115, 115"; // red or gray
  const glowOpacity = active ? 0.2 + phase * 0.6 : 0.1;

  const pulseDisplay = estimatedPulse ?? "--";
  const statusText = active
    ? "Puls erkannt via WiFi-Sensing"
    : "Warte auf stabile Messung…";

  return (
    <div className="rounded-xl border border-[#2a2a2a] bg-[#161616] p-6">
      <div className="mb-1 flex items-center justify-between">
        <h2 className="text-sm font-medium text-[#737373]">
          Vital Monitor
        </h2>
        <span className="text-xs text-[#525252]">kontaktlos via WiFi CSI</span>
      </div>

      <div className="flex flex-col items-center gap-6 sm:flex-row sm:justify-around">
        {/* Animated heart */}
        <div className="relative flex items-center justify-center" style={{ width: 180, height: 180 }}>
          {/* Glow */}
          <div
            className="absolute rounded-full blur-3xl"
            style={{
              width: 180,
              height: 180,
              background: `radial-gradient(circle, rgba(${heartColor}, ${glowOpacity * 0.6}) 0%, transparent 70%)`,
            }}
          />

          <svg
            width="140"
            height="130"
            viewBox="0 0 140 130"
            style={{
              transform: `scale(${scale})`,
              transition: "transform 0.05s linear",
              filter: active
                ? `drop-shadow(0 0 ${8 + phase * 15}px rgba(${heartColor}, ${0.3 + phase * 0.5}))`
                : "none",
            }}
          >
            {/* Heart shape */}
            <path
              d="M70 120 C70 120, 10 80, 10 45 C10 20, 30 10, 50 10 C60 10, 68 18, 70 25 C72 18, 80 10, 90 10 C110 10, 130 20, 130 45 C130 80, 70 120, 70 120Z"
              fill={`rgba(${heartColor}, ${0.25 + phase * 0.35})`}
              stroke={`rgba(${heartColor}, ${0.5 + phase * 0.5})`}
              strokeWidth="2"
            />
            {/* ECG-style line across the heart */}
            <polyline
              points="15,65 40,65 48,65 52,45 56,85 60,55 64,70 68,65 75,65 80,65 85,50 88,65 100,65 125,65"
              fill="none"
              stroke={`rgba(255,255,255,${0.3 + phase * 0.5})`}
              strokeWidth="1.5"
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          </svg>
        </div>

        {/* Stats */}
        <div className="flex flex-col items-center gap-3 sm:items-start">
          <div
            className="text-6xl font-bold tracking-tight"
            style={{
              color: active ? `rgba(${heartColor}, 1)` : "#737373",
            }}
          >
            {pulseDisplay}
            <span className="ml-2 text-lg font-normal text-[#737373]">
              BPM
            </span>
          </div>
          <div
            className="text-sm"
            style={{
              color: active ? `rgba(${heartColor}, 0.8)` : "#737373",
            }}
          >
            {statusText}
          </div>

          {/* Pulse wave bars */}
          <div className="mt-2 flex items-end gap-1">
            {Array.from({ length: 16 }).map((_, i) => {
              const bpm = estimatedPulse ?? 68;
              const cycleSec = 60 / bpm;
              const t = Date.now() / 1000;
              const rawBar = ((t + i * 0.08) % cycleSec) / cycleSec;
              let barVal: number;
              if (rawBar < 0.1) barVal = Math.sin((rawBar / 0.1) * Math.PI);
              else if (rawBar < 0.25)
                barVal = Math.sin(((rawBar - 0.1) / 0.15) * Math.PI) * 0.4;
              else barVal = 0;
              barVal = Math.max(0.08, barVal);
              return (
                <div
                  key={i}
                  className="w-1.5 rounded-full"
                  style={{
                    height: 4 + barVal * 24,
                    backgroundColor: `rgba(${heartColor}, ${0.3 + barVal * 0.7})`,
                    transition: "height 0.08s linear",
                  }}
                />
              );
            })}
          </div>

          {intensity > 10 && active && (
            <div className="mt-1 text-xs text-[#525252]">
              Bewegung erkannt — Messung ggf. ungenau
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
