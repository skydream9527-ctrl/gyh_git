import { useState } from "react";
import { userApi } from "@/api/endpoints";
import { useBackdropClose } from "@/hooks/useBackdropClose";
import { useAuthStore } from "@/stores/authStore";
import { useUIStore } from "@/stores/uiStore";
import "@/components/feedback/ConfirmModal.css";
import "./AccountModal.css";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function AccountModal({ open, onClose }: Props) {
  const user = useAuthStore((s) => s.user);
  const bootstrapMe = useAuthStore((s) => s.bootstrapMe);
  const pushToast = useUIStore((s) => s.pushToast);

  const [name, setName] = useState(user?.name || "");
  const [team, setTeam] = useState(user?.team || "");
  const [title, setTitle] = useState(user?.title || "");
  const [xiaomiEmail, setXiaomiEmail] = useState(user?.xiaomi_email || "");
  const [showPwd, setShowPwd] = useState(false);
  const [curPwd, setCurPwd] = useState("");
  const [newPwd, setNewPwd] = useState("");
  const [newPwd2, setNewPwd2] = useState("");
  const [saving, setSaving] = useState(false);

  const reset = () => {
    setName(user?.name || "");
    setTeam(user?.team || "");
    setTitle(user?.title || "");
    setXiaomiEmail(user?.xiaomi_email || "");
    setShowPwd(false);
    setCurPwd("");
    setNewPwd("");
    setNewPwd2("");
  };

  const close = () => {
    reset();
    onClose();
  };
  const backdrop = useBackdropClose(close, open);

  if (!open) return null;

  const save = async () => {
    if (!name.trim()) {
      pushToast("warning", "姓名不能为空");
      return;
    }
    const body: Parameters<typeof userApi.updateMe>[0] = {};
    if (name.trim() !== (user?.name || "")) body.name = name.trim();
    if (team !== (user?.team || "")) body.team = team || null;
    if (title !== (user?.title || "")) body.title = title || null;
    const xiaomiEmailNorm = xiaomiEmail.trim().toLowerCase();
    if (xiaomiEmailNorm !== (user?.xiaomi_email || "")) {
      if (xiaomiEmailNorm && !/^[A-Za-z0-9._\-+]+@(xiaomi|mi)\.com$/i.test(xiaomiEmailNorm)) {
        pushToast("warning", "小米办公邮箱必须是 @xiaomi.com 或 @mi.com");
        return;
      }
      body.xiaomi_email = xiaomiEmailNorm || null;
    }
    if (showPwd) {
      if (!curPwd) {
        pushToast("warning", "请输入当前密码");
        return;
      }
      if (!newPwd || newPwd !== newPwd2) {
        pushToast("warning", "两次输入的新密码不一致");
        return;
      }
      body.current_password = curPwd;
      body.new_password = newPwd;
    }
    if (Object.keys(body).length === 0) {
      pushToast("info", "未做任何修改");
      onClose();
      return;
    }
    setSaving(true);
    try {
      await userApi.updateMe(body);
      await bootstrapMe();
      pushToast("success", "账户信息已更新");
      reset();
      onClose();
    } catch (err) {
      pushToast("error", (err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="cm-overlay" {...backdrop}>
      <div className="cm-card" style={{ minWidth: 460 }}>
        <h3>编辑账户</h3>
        <div className="cm-body">
          <div className="acct-form-grid">
            <label style={{ gridColumn: "span 2" }}>
              邮箱（不可修改）
              <input value={user?.email || ""} disabled />
            </label>
            <label>
              姓名
              <input value={name} onChange={(e) => setName(e.target.value)} />
            </label>
            <label>
              角色（不可修改）
              <input value={user?.auth_role || ""} disabled />
            </label>
            <label>
              团队
              <input value={team} onChange={(e) => setTeam(e.target.value)} />
            </label>
            <label>
              职务
              <input value={title} onChange={(e) => setTitle(e.target.value)} />
            </label>
            <label style={{ gridColumn: "span 2" }}>
              小米办公邮箱
              <input
                type="email"
                value={xiaomiEmail}
                onChange={(e) => setXiaomiEmail(e.target.value)}
                placeholder="xxx@xiaomi.com — 用于飞书报告自动给你加权限"
              />
            </label>
            <label className="acct-checkbox">
              <input
                type="checkbox"
                checked={showPwd}
                onChange={(e) => setShowPwd(e.target.checked)}
              />
              <span>修改密码</span>
            </label>
            {showPwd && (
              <>
                <label style={{ gridColumn: "span 2" }}>
                  当前密码
                  <input
                    type="password"
                    value={curPwd}
                    onChange={(e) => setCurPwd(e.target.value)}
                    autoComplete="current-password"
                  />
                </label>
                <label>
                  新密码
                  <input
                    type="password"
                    value={newPwd}
                    onChange={(e) => setNewPwd(e.target.value)}
                    autoComplete="new-password"
                    placeholder="≥10 位，含 3 类字符"
                  />
                </label>
                <label>
                  再输一次
                  <input
                    type="password"
                    value={newPwd2}
                    onChange={(e) => setNewPwd2(e.target.value)}
                    autoComplete="new-password"
                  />
                </label>
              </>
            )}
          </div>
        </div>
        <div className="cm-actions">
          <button className="btn-secondary" onClick={close}>
            取消
          </button>
          <button className="btn-primary" disabled={saving} onClick={save}>
            {saving ? "保存中…" : "保存"}
          </button>
        </div>
      </div>
    </div>
  );
}
