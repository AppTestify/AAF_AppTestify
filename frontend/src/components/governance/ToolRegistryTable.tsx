import { useMemo, useState } from "react";
import type { ToolRegistryEntry, ToolRegistryResponse } from "../../api";

const METHOD_LABELS: Record<string, string> = {
  direct_api: "Direct API",
  api_mcp: "API+MCP",
  mcp: "MCP",
  roadmap: "Roadmap",
};

const STATUS_LABELS: Record<string, string> = {
  shipped: "Shipped",
  pending: "Pending",
  roadmap: "Roadmap",
};

const AGENT_TAB_ORDER = ["devops", "project_management", "finops", "devsecops"];

type ToolRegistryTableProps = {
  data: ToolRegistryResponse;
  defaultStatus?: "shipped" | "all";
  readOnly?: boolean;
};

export function ToolRegistryTable({ data, defaultStatus = "shipped", readOnly = false }: ToolRegistryTableProps) {
  const [activeAgent, setActiveAgent] = useState(AGENT_TAB_ORDER[0]);
  const [statusFilter, setStatusFilter] = useState<string>(defaultStatus === "all" ? "all" : "shipped");
  const [methodFilter, setMethodFilter] = useState<string>("all");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const sections = useMemo(() => {
    const byId = new Map(data.agents.map((a) => [a.id, a]));
    return AGENT_TAB_ORDER.map((id) => byId.get(id)).filter(Boolean) as ToolRegistryResponse["agents"];
  }, [data.agents]);

  const activeSection = sections.find((s) => s.id === activeAgent) ?? sections[0];

  const filteredTools = useMemo(() => {
    if (!activeSection) return [];
    return activeSection.tools.filter((t) => {
      if (statusFilter !== "all" && t.implementation_status !== statusFilter) return false;
      if (methodFilter !== "all" && t.method !== methodFilter) return false;
      return true;
    });
  }, [activeSection, statusFilter, methodFilter]);

  const toggleRow = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div className="tool-registry">
      <div className="tool-registry-toolbar">
        <div className="tool-registry-tabs" role="tablist" aria-label="Agent tools">
          {sections.map((section) => (
            <button
              key={section.id}
              type="button"
              role="tab"
              aria-selected={activeAgent === section.id}
              className={`tool-registry-tab ${activeAgent === section.id ? "tool-registry-tab--active" : ""}`}
              onClick={() => setActiveAgent(section.id)}
            >
              {section.label}
            </button>
          ))}
        </div>
        <div className="tool-registry-filters">
          {(["all", "shipped", "pending", "roadmap"] as const).map((s) => (
            <button
              key={s}
              type="button"
              className={`guardrail-chip guardrail-chip--neutral tool-registry-filter ${statusFilter === s ? "tool-registry-filter--active" : ""}`}
              onClick={() => setStatusFilter(s)}
            >
              {s === "all" ? "All status" : STATUS_LABELS[s]}
            </button>
          ))}
          {(["all", "direct_api", "api_mcp", "mcp", "roadmap"] as const).map((m) => (
            <button
              key={m}
              type="button"
              className={`guardrail-chip guardrail-chip--neutral tool-registry-filter ${methodFilter === m ? "tool-registry-filter--active" : ""}`}
              onClick={() => setMethodFilter(m)}
            >
              {m === "all" ? "All methods" : METHOD_LABELS[m]}
            </button>
          ))}
        </div>
        <p className="field-hint tool-registry-meta">
          {data.meta.shipped_count} shipped · {data.meta.pending_count} pending · {data.meta.roadmap_count} roadmap
          {readOnly ? " · marketing view" : ""}
        </p>
      </div>

      {activeSection ? (
        <p className="tool-registry-summary">{activeSection.summary}</p>
      ) : null}

      <div className="tool-registry-scroll">
        <table className="tool-registry-table">
          <thead>
            <tr>
              <th>Tool</th>
              <th>Method</th>
              <th>Status</th>
              <th>When it fires</th>
              <th>Returns</th>
              <th aria-label="Expand details" />
            </tr>
          </thead>
          <tbody>
            {filteredTools.map((tool) => (
              <ToolRow
                key={tool.id}
                tool={tool}
                expanded={expanded.has(tool.id)}
                onToggle={() => toggleRow(tool.id)}
              />
            ))}
          </tbody>
        </table>
        {filteredTools.length === 0 ? (
          <p className="field-hint" style={{ padding: "1rem" }}>
            No tools match the current filters.
          </p>
        ) : null}
      </div>
    </div>
  );
}

function ToolRow({
  tool,
  expanded,
  onToggle,
}: {
  tool: ToolRegistryEntry;
  expanded: boolean;
  onToggle: () => void;
}) {
  const statusClass =
    tool.implementation_status === "shipped"
      ? "pass"
      : tool.implementation_status === "pending"
        ? "warn"
        : "neutral";

  return (
    <>
      <tr className="tool-registry-row">
        <td>
          <code className="mono">{tool.function_name}()</code>
          {tool.weight > 0 ? (
            <span className="guardrail-chip guardrail-chip--neutral tool-registry-weight">w={tool.weight}</span>
          ) : null}
          {tool.extension ? (
            <span className="guardrail-chip guardrail-chip--neutral tool-registry-weight">ext</span>
          ) : null}
        </td>
        <td>
          <span className="guardrail-chip guardrail-chip--neutral">{METHOD_LABELS[tool.method] ?? tool.method}</span>
        </td>
        <td>
          <span className={`guardrail-chip guardrail-chip--${statusClass}`}>
            {STATUS_LABELS[tool.implementation_status] ?? tool.implementation_status}
          </span>
        </td>
        <td className="tool-registry-fires">{tool.fires_when}</td>
        <td>
          <div className="tool-registry-returns">
            {tool.returns.map((r) => (
              <span key={r} className="guardrail-chip guardrail-chip--neutral">
                {r}
              </span>
            ))}
          </div>
        </td>
        <td>
          <button type="button" className="btn btn-ghost tool-registry-expand" onClick={onToggle} aria-expanded={expanded}>
            {expanded ? "Hide" : "Details"}
          </button>
        </td>
      </tr>
      {expanded ? (
        <tr className="tool-registry-detail-row">
          <td colSpan={6}>
            <div className="tool-registry-detail-grid">
              <div>
                <p className="gov-hub-eyebrow">System &amp; auth</p>
                <p>
                  <strong>{tool.system}</strong>
                </p>
                <p className="field-hint">{tool.auth}</p>
              </div>
              <div>
                <p className="gov-hub-eyebrow">API endpoints</p>
                <ul className="tool-registry-mono-list">
                  {(tool.api_endpoints.length ? tool.api_endpoints : ["—"]).map((ep) => (
                    <li key={ep}>
                      <code>{ep}</code>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="gov-hub-eyebrow">MCP mappings</p>
                <ul className="tool-registry-mono-list">
                  {(tool.mcp_mappings.length ? tool.mcp_mappings : ["—"]).map((m) => (
                    <li key={m}>
                      <code>{m}</code>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="tool-registry-scenario">
                <p className="gov-hub-eyebrow">PM scenario — {tool.pm_scenario.title}</p>
                <p>{tool.pm_scenario.narrative}</p>
                {tool.jira_task ? (
                  <p className="field-hint mono">Jira: {tool.jira_task}</p>
                ) : null}
              </div>
            </div>
          </td>
        </tr>
      ) : null}
    </>
  );
}
