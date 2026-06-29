/**
 * PlanApprovalPanel — renders a pending plan as a checklist where users
 * can select which steps to approve. Supports full or partial approval.
 */
import { useMemo, useState } from "react";
import { MarkdownRenderer } from "@/components/markdown/MarkdownRendererCore";
import "./PlanApprovalPanel.css";

interface PlanStep {
  index: number;
  text: string;
}

interface Props {
  planId: string;
  planText: string;
  onApprove: (planId: string, approvedSteps?: number[]) => void;
  onReject: (planId: string) => void;
}

/** Parse numbered steps from plan markdown text. */
function parseSteps(text: string): { preamble: string; steps: PlanStep[] } {
  const lines = text.split("\n");
  const steps: PlanStep[] = [];
  let preamble = "";
  let currentStep: PlanStep | null = null;
  const stepRegex = /^\s*(\d+)\s*[.)]\s+(.*)$/;

  for (const line of lines) {
    const m = stepRegex.exec(line);
    if (m) {
      if (currentStep) steps.push(currentStep);
      currentStep = { index: parseInt(m[1], 10), text: m[2] };
    } else if (currentStep) {
      // Continuation of current step
      currentStep.text += "\n" + line;
    } else {
      preamble += line + "\n";
    }
  }
  if (currentStep) steps.push(currentStep);

  return { preamble: preamble.trim(), steps };
}

export function PlanApprovalPanel({ planId, planText, onApprove, onReject }: Props) {
  const { preamble, steps } = useMemo(() => parseSteps(planText), [planText]);
  const [checked, setChecked] = useState<Set<number>>(() => new Set(steps.map((s) => s.index)));
  const hasSteps = steps.length > 0;
  const allChecked = checked.size === steps.length;
  const noneChecked = checked.size === 0;

  const toggle = (idx: number) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const toggleAll = () => {
    if (allChecked) {
      setChecked(new Set());
    } else {
      setChecked(new Set(steps.map((s) => s.index)));
    }
  };

  const handleApprove = () => {
    if (!hasSteps || allChecked) {
      // Approve all
      onApprove(planId);
    } else {
      // Partial approval
      onApprove(planId, Array.from(checked).sort((a, b) => a - b));
    }
  };

  return (
    <div className="plan-approval-panel">
      <div className="plan-approval-header">
        <span className="plan-approval-icon">📋</span>
        <span className="plan-approval-title">Agent 提交了执行方案</span>
        <span className="plan-approval-hint">选择要执行的步骤</span>
      </div>

      {preamble && (
        <div className="plan-approval-preamble">
          <MarkdownRenderer content={preamble} />
        </div>
      )}

      {hasSteps ? (
        <div className="plan-approval-steps">
          <label className="plan-step-toggle-all">
            <input type="checkbox" checked={allChecked} onChange={toggleAll} />
            <span>全选 / 取消全选</span>
          </label>
          {steps.map((step) => (
            <label key={step.index} className="plan-step-item">
              <input
                type="checkbox"
                checked={checked.has(step.index)}
                onChange={() => toggle(step.index)}
              />
              <span className="plan-step-index">{step.index}.</span>
              <span className="plan-step-text">
                <MarkdownRenderer content={step.text.trim()} />
              </span>
            </label>
          ))}
        </div>
      ) : (
        <div className="plan-approval-raw">
          <MarkdownRenderer content={planText} />
        </div>
      )}

      <div className="plan-approval-actions">
        <button
          className="btn-primary plan-approve-btn"
          onClick={handleApprove}
          disabled={hasSteps && noneChecked}
        >
          {!hasSteps || allChecked
            ? "✅ 批准全部"
            : `✅ 批准选中 (${checked.size}/${steps.length})`}
        </button>
        <button className="btn-secondary plan-reject-btn" onClick={() => onReject(planId)}>
          ❌ 拒绝
        </button>
      </div>
    </div>
  );
}
