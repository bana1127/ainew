"use client";

import { useMemo } from "react";

export type OperatingQuarter = string; // "YYYY-Qn"

interface QuarterFilterProps {
  value: OperatingQuarter | "";
  onChange: (quarter: OperatingQuarter | "") => void;
  label?: string;
  /** how many past/future years to show (default 2) */
  yearRange?: number;
}

function getQuarterLabel(q: OperatingQuarter): string {
  const [year, qn] = q.split("-Q");
  const labels: Record<string, string> = {
    "1": "1분기 (12·1·2월)",
    "2": "2분기 (3·4·5월)",
    "3": "3분기 (6·7·8월)",
    "4": "4분기 (9·10·11월)",
  };
  return `${year}년 ${labels[qn] ?? `Q${qn}`}`;
}

/** Return the current operating quarter string for today. */
export function getCurrentOperatingQuarter(): OperatingQuarter {
  const now = new Date();
  const month = now.getMonth() + 1; // 1-indexed
  const year = now.getFullYear();
  if (month === 12) return `${year + 1}-Q1`;
  if (month <= 2) return `${year}-Q1`;
  if (month <= 5) return `${year}-Q2`;
  if (month <= 8) return `${year}-Q3`;
  return `${year}-Q4`;
}

export function QuarterFilter({ value, onChange, label = "분기 필터", yearRange = 2 }: QuarterFilterProps) {
  const quarters = useMemo(() => {
    const now = new Date();
    const currentYear = now.getFullYear();
    const options: OperatingQuarter[] = [];
    for (let y = currentYear - yearRange; y <= currentYear + 1; y++) {
      for (let q = 1; q <= 4; q++) {
        options.push(`${y}-Q${q}`);
      }
    }
    return options;
  }, [yearRange]);

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      {label && (
        <label style={{ fontSize: 13, color: "var(--text-sub)", whiteSpace: "nowrap" }}>
          {label}
        </label>
      )}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as OperatingQuarter | "")}
        style={{
          background: "var(--surface)",
          color: "var(--text-main)",
          border: "1px solid var(--border-soft)",
          borderRadius: 8,
          padding: "6px 10px",
          fontSize: 13,
          cursor: "pointer",
        }}
      >
        <option value="">전체 기간</option>
        {quarters.map((q) => (
          <option key={q} value={q}>
            {getQuarterLabel(q)}
          </option>
        ))}
      </select>
    </div>
  );
}
