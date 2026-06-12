import { useMemo, useState } from "react";

type DeepLinkCopyBarProps = {
  path: string;
  className?: string;
};

export function DeepLinkCopyBar({ path, className = "" }: DeepLinkCopyBarProps) {
  const [copied, setCopied] = useState(false);
  const fullUrl = useMemo(() => `${window.location.origin}${path}`, [path]);

  const copy = async () => {
    await navigator.clipboard.writeText(fullUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`deep-link-bar ${className}`.trim()}>
      <code className="deep-link-bar-path">{path}</code>
      <button type="button" className="btn btn-ghost btn-sm" onClick={() => void copy()}>
        {copied ? "Copied" : "Copy"}
      </button>
    </div>
  );
}
