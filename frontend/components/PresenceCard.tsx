"use client";

interface PresenceCardProps {
  presence: boolean;
}

export default function PresenceCard({ presence }: PresenceCardProps) {
  return (
    <div className="rounded-xl border border-[#2a2a2a] bg-[#161616] p-6 text-center">
      <h2 className="mb-2 text-sm font-medium text-[#737373]">Presence</h2>
      <div
        className={`text-4xl font-bold ${
          presence ? "text-[#22c55e]" : "text-[#ef4444]"
        }`}
      >
        {presence ? "YES" : "NO"}
      </div>
      <div
        className={`mt-3 mx-auto h-3 w-3 rounded-full ${
          presence ? "bg-[#22c55e] shadow-[0_0_12px_#22c55e]" : "bg-[#ef4444] shadow-[0_0_12px_#ef4444]"
        }`}
      />
    </div>
  );
}
