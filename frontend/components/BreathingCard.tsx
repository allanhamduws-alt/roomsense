"use client";

import { useRef } from "react";
import {
  LineChart,
  Line,
  ResponsiveContainer,
  YAxis,
} from "recharts";

interface BreathingCardProps {
  breathingRate: number | null;
}

const MAX_HISTORY = 30;

export default function BreathingCard({ breathingRate }: BreathingCardProps) {
  const historyRef = useRef<{ value: number }[]>([]);

  if (breathingRate !== null) {
    historyRef.current = [
      ...historyRef.current.slice(-(MAX_HISTORY - 1)),
      { value: breathingRate },
    ];
  }

  return (
    <div className="rounded-xl border border-[#2a2a2a] bg-[#161616] p-6">
      <h2 className="mb-2 text-sm font-medium text-[#737373]">
        Breathing Rate
      </h2>
      {breathingRate !== null ? (
        <>
          <div className="text-3xl font-bold text-[#3b82f6]">
            {breathingRate}{" "}
            <span className="text-base font-normal text-[#737373]">BPM</span>
          </div>
          {historyRef.current.length > 2 && (
            <div className="mt-3">
              <ResponsiveContainer width="100%" height={50}>
                <LineChart data={historyRef.current}>
                  <YAxis hide domain={["auto", "auto"]} />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#3b82f6"
                    strokeWidth={1.5}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      ) : (
        <div className="text-xl text-[#737373]">Collecting data…</div>
      )}
    </div>
  );
}
