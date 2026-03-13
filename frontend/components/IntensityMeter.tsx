"use client";

interface IntensityMeterProps {
  intensity: number;
}

export default function IntensityMeter({ intensity }: IntensityMeterProps) {
  const clampedIntensity = Math.min(100, Math.max(0, intensity));

  const getColor = () => {
    if (clampedIntensity < 20) return "#22c55e";
    if (clampedIntensity < 50) return "#eab308";
    return "#ef4444";
  };

  return (
    <div className="rounded-xl border border-[#2a2a2a] bg-[#161616] p-6">
      <h2 className="mb-2 text-sm font-medium text-[#737373]">
        Movement Intensity
      </h2>
      <div className="text-3xl font-bold" style={{ color: getColor() }}>
        {Math.round(clampedIntensity)}
      </div>
      <div className="mt-3 h-2 w-full rounded-full bg-[#2a2a2a]">
        <div
          className="h-2 rounded-full transition-all duration-300"
          style={{
            width: `${clampedIntensity}%`,
            backgroundColor: getColor(),
          }}
        />
      </div>
      <div className="mt-1 flex justify-between text-xs text-[#737373]">
        <span>0</span>
        <span>100</span>
      </div>
    </div>
  );
}
