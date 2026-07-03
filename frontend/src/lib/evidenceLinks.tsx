import type { ReactNode } from "react";
import type { EvidenceRecord } from "../api";

export type EvidenceLink = { label: string; href: string };

const JIRA_KEY_RE = /\b([A-Z][A-Z0-9]+-\d+)\b/g;

export function getEvidenceLinks(record?: EvidenceRecord | null): EvidenceLink[] {
  if (!record?.metadata) return [];
  const meta = record.metadata;
  const url = meta.url;
  if (typeof url === "string" && url.startsWith("http")) {
    let label = "Open";
    if (typeof meta.key === "string" && meta.key) label = meta.key;
    else if (typeof meta.number === "number") label = `PR #${meta.number}`;
    else if (record.kind === "workflow_run") label = "Workflow run";
    else if (record.kind === "open_mr" && meta.iid) label = `MR !${meta.iid}`;
    else if (record.kind === "pipeline" && meta.id) label = `Pipeline #${meta.id}`;
    else if (record.kind === "open_issue" && meta.iid && record.source === "gitlab") label = `Issue #${meta.iid}`;

    return [{ label, href: url }];
  }
  if (typeof meta.key === "string" && meta.key && typeof meta.jira_base_url === "string") {
    const base = meta.jira_base_url.replace(/\/$/, "");
    return [{ label: meta.key, href: `${base}/browse/${meta.key}` }];
  }
  return [];
}

export function linkifyEvidenceText(text: string, jiraBaseUrl?: string | null): ReactNode {
  if (!text) return text;
  const parts: ReactNode[] = [];
  let last = 0;
  let match: RegExpExecArray | null;
  const re = new RegExp(JIRA_KEY_RE.source, "g");
  while ((match = re.exec(text)) !== null) {
    if (match.index > last) {
      parts.push(text.slice(last, match.index));
    }
    const key = match[1];
    const base = jiraBaseUrl?.replace(/\/$/, "");
    if (base) {
      parts.push(
        <a key={`${key}-${match.index}`} href={`${base}/browse/${key}`} target="_blank" rel="noreferrer">
          {key}
        </a>
      );
    } else {
      parts.push(key);
    }
    last = match.index + match[0].length;
  }
  if (last < text.length) {
    parts.push(text.slice(last));
  }
  return parts.length > 0 ? parts : text;
}

type EvidenceDetailCellProps = {
  detail: string;
  record?: EvidenceRecord;
  jiraBaseUrl?: string | null;
};

export function EvidenceDetailCell({ detail, record, jiraBaseUrl }: EvidenceDetailCellProps) {
  const links = getEvidenceLinks(record);
  if (links.length > 0) {
    return (
      <span className="evidence-detail-cell">
        {links.map((link) => (
          <a key={link.href} href={link.href} target="_blank" rel="noreferrer" className="evidence-external-link">
            {link.label}
          </a>
        ))}
        <span className="evidence-detail-text"> — {linkifyEvidenceText(detail, jiraBaseUrl)}</span>
      </span>
    );
  }
  return <span className="evidence-detail-cell">{linkifyEvidenceText(detail, jiraBaseUrl)}</span>;
}
