import { useEffect, useState } from "react";
import { fetchDashboardSummary, type DashboardSummary } from "../api";

export function useDashboardSummary() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = () => {
    setLoading(true);
    setError(null);
    return fetchDashboardSummary()
      .then(setSummary)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load dashboard summary"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    void reload();
  }, []);

  return { summary, loading, error, reload };
}
