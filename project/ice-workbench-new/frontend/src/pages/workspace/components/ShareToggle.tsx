/**
 * Share/unshare toggle button for tasks.
 * Extracted from WorkspacePage.tsx.
 */
import { useState } from "react";
import { shareApi } from "@/api/endpoints";
import { useUIStore } from "@/stores/uiStore";

interface Props {
  taskId: string;
  visibility: string;
  publishStatus?: string;
  onChanged: () => void | Promise<void>;
}

export function ShareToggle({ taskId, visibility, publishStatus, onChanged }: Props) {
  const pushToast = useUIStore((s) => s.pushToast);
  const [busy, setBusy] = useState(false);
  const isPublic = visibility === "public";
  const isPending = publishStatus === "pending";
  const isRejected = publishStatus === "rejected";
  const click = async () => {
    setBusy(true);
    try {
      if (isPublic) {
        await shareApi.unshare(taskId);
        pushToast("success", "已撤回到私有");
      } else {
        const r = await shareApi.share(taskId);
        pushToast(
          r.publish_status === "pending" ? "info" : "success",
          r.publish_status === "pending" ? "已提交审核，admin 通过后才会展示" : "已发布到公共区",
        );
      }
      await onChanged();
    } catch (err) {
      pushToast("error", (err as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <button
      className="btn-ghost"
      onClick={click}
      disabled={busy}
      title={isPending ? "审核中" : isRejected ? "审核未通过，可重新开放给团队" : isPublic ? "撤回到私有" : "任务开放给团队"}
    >
      {isPending ? "🕓 审核中" : isRejected ? "🚫 已驳回" : isPublic ? "🔗 已开放给团队" : "🔗 任务开放给团队"}
    </button>
  );
}
