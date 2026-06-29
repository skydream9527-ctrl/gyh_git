/**
 * HITL (Human-in-the-Loop) intervention card — renders when the agent
 * requests human confirmation/input before proceeding.
 * Extracted from WorkspacePage.tsx.
 */
import { useState } from "react";
import { MarkdownRenderer } from "@/components/markdown/MarkdownRenderer";
import type { HitlRequest } from "@/types/api";

interface Props {
  taskName: string;
  request: HitlRequest | null;
  busy: boolean;
  onOpenSandbox: () => void;
  onContinue: (payload: Record<string, unknown>, decision: string, note: string) => void | Promise<void>;
}

export function V6HumanInterventionCard({
  taskName,
  request,
  busy,
  onOpenSandbox,
  onContinue,
}: Props) {
  const [values, setValues] = useState<Record<string, string>>({});
  const fields = request?.fields?.length
    ? request.fields
    : [
        { id: "note", label: "处理说明", value: "", placeholder: "补充判断依据或修正口径" },
      ];
  const columns = request?.table?.columns || [];
  const rows = request?.table?.rows || [];
  const primaryAction = request?.actions?.[0]?.id || "continue";
  const note = values.note || "";
  const submit = (decision: string) => {
    const payload = {
      fields: Object.fromEntries(fields.map((f) => [f.id, values[f.id] ?? f.value ?? ""])),
      table_rows: rows,
    };
    onContinue(payload, decision, note);
  };

  return (
    <div className="v6-hitl-card v6-hitl-inline">
      <div className="v6-hitl-head">
        <div className="v6-hitl-title">
          <span className="v6-pulse" />
          检测到需要人工确认的节点
        </div>
        <span className="v6-badge v6-badge-warning">HITL</span>
      </div>
      <div className="v6-hitl-body">
        <div className="v6-hitl-message">
          <MarkdownRenderer
            content={request?.message || `工作流「${taskName}」已挂起。请补充处理口径，确认后 Agent 会继续执行。`}
          />
        </div>
        {rows.length > 0 && columns.length > 0 && (
          <div className="v6-hitl-table">
            <div className="v6-hitl-tr head">
              {columns.map((c) => <span key={c}>{c}</span>)}
            </div>
            {rows.slice(0, 4).map((row, idx) => (
              <div className="v6-hitl-tr" key={idx}>
                {columns.map((c) => <span key={c}>{String(row[c] ?? "")}</span>)}
              </div>
            ))}
          </div>
        )}
        <div className="v6-hitl-fields">
          {fields.map((field) => (
            <label className="v6-hitl-field" key={field.id}>
              <span>
                {field.label}
                {field.required && <b>*</b>}
              </span>
              <input
                value={values[field.id] ?? field.value ?? ""}
                onChange={(e) => setValues((cur) => ({ ...cur, [field.id]: e.target.value }))}
                placeholder={field.placeholder || "请输入"}
              />
            </label>
          ))}
        </div>
        <div className="v6-hitl-actions">
          <button type="button" className="v6-btn-primary" disabled={busy || !request} onClick={() => submit(primaryAction)}>
            {busy ? "处理中..." : request?.actions?.[0]?.label || "确认并继续"}
          </button>
          <button type="button" className="v6-btn-outline" disabled={busy || !request} onClick={() => submit("skip")}>
            跳过该节点
          </button>
          <button type="button" className="v6-hitl-link" onClick={onOpenSandbox}>打开沙盒</button>
        </div>
      </div>
    </div>
  );
}
