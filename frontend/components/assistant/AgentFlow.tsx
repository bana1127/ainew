import { ArrowRight } from "lucide-react";

export function AgentFlow({ steps }: { steps: string[] }) {
  if (!steps || steps.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {steps.map((step, i) => (
        <span key={i} className="flex items-center gap-1.5">
          <span
            className="rounded-lg px-2 py-0.5 text-xs font-medium"
            style={{ background: "var(--primary-soft)", color: "var(--primary)" }}
          >
            {step}
          </span>
          {i < steps.length - 1 && (
            <ArrowRight className="h-3 w-3 shrink-0" style={{ color: "var(--text-muted)" }} />
          )}
        </span>
      ))}
    </div>
  );
}
