import type { LucideIcon } from "lucide-react";

type Tone = "success" | "warning" | "danger" | "neutral";

const toneStyles: Record<Tone, string> = {
  success: "border-pine/30 bg-pine/10 text-pine",
  warning: "border-amber/30 bg-amber/10 text-amber",
  danger: "border-coral/30 bg-coral/10 text-coral",
  neutral: "border-line bg-white text-ink",
};

export function StatCard({
  icon: Icon,
  label,
  value,
  tone = "neutral",
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  tone?: Tone;
}) {
  return (
    <div className="rounded-lg border border-line bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-gray-500">{label}</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{value}</p>
        </div>
        <div className={`rounded-md border p-3 ${toneStyles[tone]}`}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
      </div>
    </div>
  );
}

