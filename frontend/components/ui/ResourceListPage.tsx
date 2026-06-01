"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import type { ApiRecord } from "@/lib/api";

type Column = {
  key: string;
  label: string;
};

function valueToText(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

export function ResourceListPage({
  title,
  description,
  load,
  columns,
}: {
  title: string;
  description: string;
  load: () => Promise<ApiRecord[]>;
  columns: Column[];
}) {
  const [items, setItems] = useState<ApiRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    load()
      .then((data) => {
        setItems(data);
        setError(null);
      })
      .catch((err: Error) => {
        setError(err.message || "데이터를 불러오지 못했습니다.");
      })
      .finally(() => setLoading(false));
  }, [load]);

  return (
    <AppShell>
      <section className="space-y-5">
        <div>
          <h1 className="text-2xl font-semibold text-ink">{title}</h1>
          <p className="mt-2 text-sm text-gray-600">{description}</p>
        </div>

        <div className="rounded-lg border border-line bg-white shadow-sm">
          {loading ? (
            <div className="p-6 text-sm text-gray-600">Loading...</div>
          ) : error ? (
            <div className="p-6 text-sm text-coral">{error}</div>
          ) : items.length === 0 ? (
            <div className="p-6 text-sm text-gray-600">표시할 데이터가 없습니다.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-line text-sm">
                <thead className="bg-mist">
                  <tr>
                    {columns.map((column) => (
                      <th
                        key={column.key}
                        className="px-4 py-3 text-left font-semibold text-ink"
                      >
                        {column.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {items.map((item, index) => (
                    <tr key={item.id ?? item.key ?? index}>
                      {columns.map((column) => (
                        <td key={column.key} className="max-w-xs px-4 py-3 text-gray-700">
                          <span className="line-clamp-2">
                            {valueToText(item[column.key])}
                          </span>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </AppShell>
  );
}

