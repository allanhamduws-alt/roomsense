"use client";

import { useEffect, useRef, useState } from "react";
import LiveCSIGraph from "@/components/LiveCSIGraph";
import PresenceCard from "@/components/PresenceCard";
import ActivityCard from "@/components/ActivityCard";
import BreathingCard from "@/components/BreathingCard";
import IntensityMeter from "@/components/IntensityMeter";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const WS_URL = BACKEND_URL.replace(/^http/, "ws") + "/ws";

interface Status {
  presence: boolean;
  activity: string;
  intensity: number;
  breathing_rate: number | null;
  amplitudes: number[];
}

export default function Dashboard() {
  const [status, setStatus] = useState<Status>({
    presence: false,
    activity: "empty",
    intensity: 0,
    breathing_rate: null,
    amplitudes: new Array(64).fill(0),
  });
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let reconnectTimeout: NodeJS.Timeout;

    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        // Send a ping to keep connection alive
        ws.send("ping");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as Status;
          setStatus(data);
        } catch {
          // ignore non-JSON messages
        }
      };

      ws.onclose = () => {
        setConnected(false);
        reconnectTimeout = setTimeout(connect, 2000);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      clearTimeout(reconnectTimeout);
      wsRef.current?.close();
    };
  }, []);

  // Send periodic pings to keep WebSocket alive
  useEffect(() => {
    const interval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send("ping");
      }
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <div className="flex items-center gap-2 text-sm">
          <div
            className={`h-2 w-2 rounded-full ${
              connected ? "bg-[#22c55e]" : "bg-[#ef4444]"
            }`}
          />
          <span className="text-[#737373]">
            {connected ? "Live" : "Disconnected"}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <PresenceCard presence={status.presence} />
        <ActivityCard activity={status.activity} />
        <IntensityMeter intensity={status.intensity} />
        <BreathingCard breathingRate={status.breathing_rate} />
      </div>

      <LiveCSIGraph amplitudes={status.amplitudes} />
    </div>
  );
}
