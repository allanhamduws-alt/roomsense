"use client";

interface ActivityCardProps {
  activity: string;
}

const activityConfig: Record<string, { icon: string; color: string }> = {
  empty: { icon: "🚫", color: "#737373" },
  still: { icon: "🧍", color: "#3b82f6" },
  sitting: { icon: "🪑", color: "#22c55e" },
  walking: { icon: "🚶", color: "#eab308" },
  lying: { icon: "🛏️", color: "#a855f7" },
};

export default function ActivityCard({ activity }: ActivityCardProps) {
  const config = activityConfig[activity] || activityConfig.empty;

  return (
    <div className="rounded-xl border border-[#2a2a2a] bg-[#161616] p-6 text-center">
      <h2 className="mb-2 text-sm font-medium text-[#737373]">Activity</h2>
      <div className="text-4xl">{config.icon}</div>
      <div
        className="mt-2 text-lg font-semibold capitalize"
        style={{ color: config.color }}
      >
        {activity}
      </div>
    </div>
  );
}
