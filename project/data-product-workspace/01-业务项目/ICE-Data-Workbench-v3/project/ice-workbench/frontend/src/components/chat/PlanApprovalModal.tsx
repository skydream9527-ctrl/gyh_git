import type { PlanProposal } from "@/hooks/useChatSocket";
import "./PlanApprovalModal.css";

interface Props {
  proposal: PlanProposal;
  onApprove: (planId: string) => void;
  onReject: (planId: string) => void;
}

/** Modal shown when the agent calls `exit_plan_mode`. Blocks interaction until
 * the user decides. On approve the backend injects a synthetic user message
 * so the agent re-runs the plan end-to-end without the user typing. */
function PlanApprovalModal({ proposal, onApprove, onReject }: Props) {
  return (
    <div className="plan-modal__backdrop" role="dialog" aria-modal="true">
      <div className="plan-modal">
        <div className="plan-modal__head">
          <div className="plan-modal__title">Agent 提交了方案，等待你批准</div>
          <div className="plan-modal__hint">
            批准后 agent 会自动开始执行；拒绝后你可以继续在输入框里补充要求。
          </div>
        </div>
        <div className="plan-modal__body">{proposal.plan_text}</div>
        <div className="plan-modal__actions">
          <button
            className="plan-modal__btn reject"
            onClick={() => onReject(proposal.plan_id)}
          >
            拒绝
          </button>
          <button
            className="plan-modal__btn approve"
            onClick={() => onApprove(proposal.plan_id)}
          >
            批准并执行
          </button>
        </div>
      </div>
    </div>
  );
}

export default PlanApprovalModal;
