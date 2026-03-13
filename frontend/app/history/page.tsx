"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

interface Event {
  id: number;
  timestamp: string;
  presence: number;
  activity: string;
  intensity: number;
  breathing_rate: number | null;
}

const activityToNum: Record<string, number> = {
  empty: 0,
  still: 1,
  lying: 2,
  sitting: 3,
  walking: 4,
};

export default function HistoryPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${BACKEND_URL}/history?limit=200`)
      .then((r) => r.json())
      .then((data) => {
        // Reverse so oldest is first (chart left to right)
        setEvents(data.reverse());
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const chartData = events.map((e) => ({
    time: new Date(e.timestamp).toLocaleTimeString(),
    presence: e.presence,
    activity: activityToNum[e.activity] ?? 0,
    intensity: e.intensity,
    breathing: e.breathing_rate,
  }));

  if (loading) {
    return <div className="text-[#737373]">Loading history…</div>;
  }

  if (events.length === 0) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">History</h1>
        <p className="text-[#737373]">No events recorded yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">History</h1>

      <div className="rounded-xl border border-[#2a2a2a] bg-[#161616] p-4">
        <h2 className="mb-3 text-sm font-medium text-[#737373]">
          Presence & Intensity over Time
        </h2>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
            <XAxis
              dataKey="time"
              stroke="#737373"
              tick={{ fontSize: 10 }}
              interval="preserveStartEnd"
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
            <Legend />
            <Line
              type="stepAfter"
              dataKey="presence"
              stroke="#22c55e"
              strokeWidth={2}
              dot={false}
              name="Presence"
            />
            <Line
              type="monotone"
              dataKey="intensity"
              stroke="#eab308"
              strokeWidth={1.5}
              dot={false}
              name="Intensity"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="rounded-xl border border-[#2a2a2a] bg-[#161616] p-4">
        <h2 className="mb-3 text-sm font-medium text-[#737373]">
          Activity & Breathing over Time
        </h2>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
            <XAxis
              dataKey="time"
              stroke="#737373"
              tick={{ fontSize: 10 }}
              interval="preserveStartEnd"
            />
            <YAxis
              yAxisId="left"
              stroke="#737373"
              tick={{ fontSize: 10 }}
              domain={[0, 4]}
              ticks={[0, 1, 2, 3, 4]}
              tickFormatter={(v) =>
                ["empty", "still", "lying", "sitting", "walking"][v] || ""
              }
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              stroke="#737373"
              tick={{ fontSize: 10 }}
            />
            <Tooltip
              contentStyle={{
                background: "#161616",
                border: "1px solid #2a2a2a",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Legend />
            <Line
              yAxisId="left"
              type="stepAfter"
              dataKey="activity"
              stroke="#a855f7"
              strokeWidth={2}
              dot={false}
              name="Activity"
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="breathing"
              stroke="#3b82f6"
              strokeWidth={1.5}
              dot={false}
              name="Breathing (BPM)"
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="rounded-xl border border-[#2a2a2a] bg-[#161616] p-4">
        <h2 className="mb-3 text-sm font-medium text-[#737373]">
          Recent Events
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-[#737373]">
              <tr>
                <th className="pb-2">Time</th>
                <th className="pb-2">Presence</th>
                <th className="pb-2">Activity</th>
                <th className="pb-2">Intensity</th>
                <th className="pb-2">Breathing</th>
              </tr>
            </thead>
            <tbody>
              {events
                .slice(-20)
                .reverse()
                .map((e) => (
                  <tr key={e.id} className="border-t border-[#2a2a2a]">
                    <td className="py-2">
                      {new Date(e.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="py-2">
                      <span
                        className={
                          e.presence ? "text-[#22c55e]" : "text-[#ef4444]"
                        }
                      >
                        {e.presence ? "Yes" : "No"}
                      </span>
                    </td>
                    <td className="py-2 capitalize">{e.activity}</td>
                    <td className="py-2">{e.intensity}</td>
                    <td className="py-2">
                      {e.breathing_rate !== null
                        ? `${e.breathing_rate} BPM`
                        : "–"}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
