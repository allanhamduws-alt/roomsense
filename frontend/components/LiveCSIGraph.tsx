"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

interface LiveCSIGraphProps {
  amplitudes: number[];
}

export default function LiveCSIGraph({ amplitudes }: LiveCSIGraphProps) {
  const data = amplitudes.map((amp, i) => ({
    subcarrier: i,
    amplitude: Math.round(amp * 100) / 100,
  }));

  return (
    <div className="rounded-xl border border-[#2a2a2a] bg-[#161616] p-4">
      <h2 className="mb-3 text-sm font-medium text-[#737373]">
        Live CSI – 64 Subcarriers
      </h2>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
          <XAxis
            dataKey="subcarrier"
            stroke="#737373"
            tick={{ fontSize: 10 }}
            tickCount={8}
          />
          <YAxis stroke="#737373" tick={{ fontSize: 10 }} />
          <Tooltip
            contentStyle={{
              background: "#161616",
              border: "1px solid #2a2a2a",
              borderRadius: 8,
              fontSize: 12,
            }}
          />
          <Line
            type="monotone"
            dataKey="amplitude"
            stroke="#3b82f6"
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
