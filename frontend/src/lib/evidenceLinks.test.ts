import { describe, expect, it } from "vitest";
import { getEvidenceLinks } from "./evidenceLinks";
import type { EvidenceRecord } from "../api";

describe("evidenceLinks", () => {
  it("returns Jira browse URL from metadata", () => {
    const record: EvidenceRecord = {
      source: "jira",
      kind: "blocked_issue",
      summary: "PAY-441: Blocked deploy [Blocked]",
      severity: 0.8,
      metadata: {
        key: "PAY-441",
        url: "https://apptestify.atlassian.net/browse/PAY-441",
        jira_base_url: "https://apptestify.atlassian.net",
      },
    };
    expect(getEvidenceLinks(record)).toEqual([
      { label: "PAY-441", href: "https://apptestify.atlassian.net/browse/PAY-441" },
    ]);
  });

  it("returns GitHub PR URL from metadata", () => {
    const record: EvidenceRecord = {
      source: "github",
      kind: "open_pr",
      summary: "Release candidate",
      severity: 0.35,
      metadata: {
        number: 42,
        url: "https://github.com/apptestify/payment-service/pull/42",
      },
    };
    expect(getEvidenceLinks(record)).toEqual([
      { label: "PR #42", href: "https://github.com/apptestify/payment-service/pull/42" },
    ]);
  });
});
