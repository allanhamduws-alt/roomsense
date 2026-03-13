"use client";

import { useEffect, useRef, useState } from "react";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const WS_URL = BACKEND_URL.replace(/^http/, "ws") + "/ws";

const LABELS = ["empty", "still", "sitting", "walking", "lying"] as const;
const RECORD_DURATION = 30; // seconds

export default function CalibratePage() {
  const [recording, setRecording] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<string | null>(null);
  const snapshotsRef = useRef<number[][]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => ws.send("ping");

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (recording && data.amplitudes) {
          snapshotsRef.current.push(data.amplitudes);
        }
      } catch {
        // ignore
      }
    };

    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send("ping");
    }, 5000);

    return () => {
      clearInterval(pingInterval);
      ws.close();
    };
  }, [recording]);

  async function startCalibration(label: string) {
    snapshotsRef.current = [];
    setRecording(label);
    setProgress(0);
    setResult(null);

    // Collect for RECORD_DURATION seconds
    for (let i = 0; i <= RECORD_DURATION; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      setProgress(Math.round((i / RECORD_DURATION) * 100));
    }

    // Send to backend
    try {
      const res = await fetch(`${BACKEND_URL}/calibrate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          label,
          snapshots: snapshotsRef.current,
        }),
      });
      const data = await res.json();
      setResult(
        `Calibration saved: ${data.samples} samples, threshold: ${data.threshold}`
      );
    } catch (err) {
      setResult("Error: Could not save calibration");
    }

    setRecording(null);
    setProgress(0);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Calibration</h1>
      <p className="text-[#737373]">
        Record a 30-second baseline for each activity. Make sure the room
        matches the selected condition.
      </p>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {LABELS.map((label) => (
          <button
            key={label}
            onClick={() => startCalibration(label)}
            disabled={recording !== null}
            className={`rounded-xl border border-[#2a2a2a] bg-[#161616] p-6 text-left transition hover:border-[#3b82f6] disabled:opacity-50 disabled:cursor-not-allowed ${
              recording === label ? "border-[#3b82f6]" : ""
            }`}
          >
            <div className="text-lg font-semibold capitalize">{label}</div>
            <div className="mt-1 text-sm text-[#737373]">
              {recording === label
                ? `Recording… ${progress}%`
                : "Click to start"}
            </div>
            {recording === label && (
              <div className="mt-3 h-1.5 w-full rounded-full bg-[#2a2a2a]">
                <div
                  className="h-1.5 rounded-full bg-[#3b82f6] transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            )}
          </button>
        ))}
      </div>

      {result && (
        <div className="rounded-xl border border-[#2a2a2a] bg-[#161616] p-4 text-sm">
          {result}
        </div>
      )}
    </div>
  );
}
