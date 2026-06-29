import { useNavigate } from "react-router-dom";
import { scheduledApi } from "@/api/endpoints";
import type { ScheduledTask } from "@/api/endpoints";
import { Skeleton } from "@/components/feedback/Skeleton";
import ConversationTab from "@/components/task/ConversationTab";
import { ExecutionCockpit } from "@/components/task/ExecutionCockpit";
import { V6ExecutionPlan } from "./components/V6ExecutionPlan";
import { shortDesc } from "./utils";
import type {
  AgentCard,
  ConversationSummary,
  SkillCard,
  TaskDetail,
} from "@/types/api";

import type { StreamPhase, InflightUser, TodoItem, PlanProposal, RunEvent } from "@/hooks/useChatSocket";

export interface WorkspaceRightPanelProps {
  task: TaskDetail;
  taskId: string;
  agent: AgentCard | null;
  // Socket-derived
  phase: StreamPhase;
  status: "idle" | "connecting" | "open" | "closed";
  todos: TodoItem[];
  todosUpdatedAt: string | null;
  runEvents: RunEvent[];
  planMode: boolean;
  pendingPlan: PlanProposal | null;
  inflightUser: InflightUser | null;
  // Tabs
  activeRightTab: "execution" | "conv" | "scheduled" | "skill" | "agent";
  onSetActiveRightTab: (tab: "execution" | "conv" | "scheduled" | "skill" | "agent") => void;
  // Execution tab
  currentUserId: string | undefined;
  scheduledItems: ScheduledTask[];
  canWrite: boolean;
  onTogglePlanMode: () => void;
  onApprovePlan: (pid: string) => void;
  onRejectPlan: (pid: string) => void;
  onOpenScheduled: () => void;
  // Conversation tab
  conversationId: string | null;
  convListReloadKey: number;
  onConvItemsLoaded: (items: ConversationSummary[]) => void;
  onConvSelect: (cid: string) => Promise<void>;
  // Scheduled tab
  onReloadScheduled: () => Promise<void>;
  // Skill tab
  allSkills: SkillCard[];
  skillPickerOpen: boolean;
  onSkillPickerToggle: () => void;
  skillBusy: boolean;
  onUpdateSkills: (next: string[]) => Promise<void>;
  // Agent tab
  agentFiles: { path: string; name: string; size: number; dir: string; text: boolean; ext: string }[];
  agentFilePreview: { path: string; name: string; content: string | null; binary: boolean; truncated?: boolean } | null;
  agentFileLoading: boolean;
  onAgentFileClick: (path: string) => void;
  onAgentFilePreviewClose: () => void;
  // General
  pushToast: (type: "success" | "error" | "info", msg: string) => void;
}

export function WorkspaceRightPanel({
  task,
  taskId,
  agent,
  phase,
  status,
  todos,
  todosUpdatedAt,
  runEvents,
  planMode,
  pendingPlan,
  inflightUser,
  activeRightTab,
  onSetActiveRightTab,
  currentUserId,
  scheduledItems,
  canWrite,
  onTogglePlanMode,
  onApprovePlan,
  onRejectPlan,
  onOpenScheduled,
  conversationId,
  convListReloadKey,
  onConvItemsLoaded,
  onConvSelect,
  onReloadScheduled,
  allSkills,
  skillPickerOpen,
  onSkillPickerToggle,
  skillBusy,
  onUpdateSkills,
  agentFiles,
  agentFilePreview,
  agentFileLoading,
  onAgentFileClick,
  onAgentFilePreviewClose,
  pushToast,
}: WorkspaceRightPanelProps) {
  const navigate = useNavigate();

  const skillIds = task?.skill_ids ?? [];
  const skillsById = new Map(allSkills.map((s) => [s.id, s]));

  const removeSkill = (sid: string) =>
    onUpdateSkills(skillIds.filter((x) => x !== sid));
  const addSkill = (sid: string) => {
    if (skillIds.includes(sid)) return;
    onUpdateSkills([...skillIds, sid]);
  };

  return (
    <aside className="ws-right">
      <div className="v6-pane-header"><h3 className="v6-pane-title">Execution & Tools</h3></div>
      <V6ExecutionPlan
        todos={todos}
        runEvents={runEvents}
        phase={phase}
        pendingPlan={Boolean(pendingPlan)}
        inflightName={inflightUser?.name || null}
        scheduledCount={scheduledItems.length}
        agentName={agent?.name || task.agent_id || "Agent"}
      />
      <div className="ws-right-tabs">
        {(
          [
            { k: "execution", label: "◎ 执行" },
            { k: "conv", label: "💬 对话" },
            { k: "scheduled", label: "⏱ 定时任务" },
            { k: "skill", label: "🧰 Skill" },
            { k: "agent", label: "🤖 Agent" },
          ] as const
        ).map((t) => (
          <button
            key={t.k}
            className={activeRightTab === t.k ? "active" : ""}
            onClick={() => onSetActiveRightTab(t.k)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="ws-right-body">
        {activeRightTab === "execution" && (
          <ExecutionCockpit
            task={task}
            agent={agent}
            phase={phase}
            status={status}
            runEvents={runEvents}
            todos={todos}
            todosUpdatedAt={todosUpdatedAt}
            planMode={planMode}
            pendingPlan={pendingPlan}
            inflightUser={inflightUser}
            currentUserId={currentUserId}
            scheduledItems={scheduledItems}
            canWrite={canWrite}
            onTogglePlanMode={onTogglePlanMode}
            onApprovePlan={onApprovePlan}
            onRejectPlan={onRejectPlan}
            onOpenScheduled={onOpenScheduled}
          />
        )}
        {activeRightTab === "agent" && (
          <div className="ws-agent-tab">
            {agent ? (
              <>
                <div className="ws-agent-head">
                  <span style={{ fontSize: 28 }}>{agent.icon}</span>
                  <div>
                    <div className="ws-agent-name">{agent.name}</div>
                    <div className="ws-agent-paradigm">{agent.paradigm}</div>
                  </div>
                </div>
                <p className="ws-agent-desc">{agent.description}</p>
              </>
            ) : (
              <div className="ws-empty">未绑定 Agent</div>
            )}

            {/* Agent 目录下的全部文件 */}
            {agent && (
              <div className="ws-agent-files-section">
                <div className="ws-skill-head">
                  📂 Agent 文件（<code>agents/{agent.id}/</code>）
                </div>
                {agentFiles.length === 0 ? (
                  <div className="ws-empty">暂无文件</div>
                ) : (
                  <ul className="ws-agent-files">
                    {agentFiles.map((f) => {
                      const isActive = agentFilePreview?.path === f.path;
                      return (
                        <li key={f.path}>
                          <button
                            type="button"
                            className={`ws-agent-file-btn${isActive ? " is-active" : ""}${f.text ? "" : " is-binary"}`}
                            title={f.path + (f.text ? "" : " · 二进制，仅展示")}
                            onClick={() => onAgentFileClick(f.path)}
                          >
                            <span className="ws-af-icon">
                              {f.ext === "json" ? "🔧" : f.ext === "md" ? "📄" : f.ext === "py" ? "🐍" : f.text ? "📝" : "📦"}
                            </span>
                            <span className="ws-af-path">{f.path}</span>
                            <span className="ws-af-size">{f.size} B</span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
                {agentFilePreview && (
                  <div className="ws-agent-file-preview">
                    <div className="ws-agent-file-preview-head">
                      <span>{agentFilePreview.name}</span>
                      <button
                        type="button"
                        className="ws-af-close"
                        onClick={onAgentFilePreviewClose}
                        title="关闭"
                      >
                        ×
                      </button>
                    </div>
                    {agentFileLoading ? (
                      <Skeleton lines={4} />
                    ) : agentFilePreview.binary ? (
                      <div className="ws-empty">二进制文件，无法预览</div>
                    ) : (
                      <pre className="ws-af-pre">{agentFilePreview.content}</pre>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
        {activeRightTab === "skill" && (
          <div className="ws-skill-tab">
            <div className="ws-skill-section">
              <div className="ws-skill-head-row">
                <span className="ws-skill-head">🧰 本任务 Skills</span>
                {canWrite && (
                  <button
                    type="button"
                    className="ws-skill-add-btn"
                    disabled={skillBusy}
                    onClick={onSkillPickerToggle}
                    title="添加 / 管理 skill"
                  >
                    {skillPickerOpen ? "收起" : "＋ 添加"}
                  </button>
                )}
              </div>
              {skillIds.length === 0 ? (
                <div className="ws-empty">未绑定任何 skill</div>
              ) : (
                <ul className="ws-skill-list">
                  {skillIds.map((sid) => {
                    const s = skillsById.get(sid);
                    const label = s?.name ?? sid;
                    const desc = s?.description_zh || s?.description || "";
                    const cat = s?.category ?? "unknown";
                    return (
                      <li key={sid} className="ws-skill-item" title={desc}>
                        <div className="ws-skill-row">
                          <span className={`ws-skill-badge ws-skill-badge-${cat}`}>
                            {cat === "builtin" ? "内置" : cat === "agentic" ? "agentic" : cat}
                          </span>
                          <span className="ws-skill-name">{label}</span>
                          {canWrite && (
                            <button
                              type="button"
                              className="ws-skill-remove"
                              disabled={skillBusy}
                              title="从任务中移除"
                              onClick={() => removeSkill(sid)}
                            >
                              ×
                            </button>
                          )}
                        </div>
                        {desc && <div className="ws-skill-desc">{shortDesc(desc)}</div>}
                      </li>
                    );
                  })}
                </ul>
              )}
              {skillPickerOpen && canWrite && (
                <div className="ws-skill-picker">
                  <div className="ws-skill-picker-head">选择要添加的 skill</div>
                  {(() => {
                    const candidates = allSkills.filter(
                      (s) => !skillIds.includes(s.id),
                    );
                    if (candidates.length === 0) {
                      return <div className="ws-empty">没有更多可添加的 skill</div>;
                    }
                    return (
                      <ul className="ws-skill-list ws-skill-picker-list">
                        {candidates.map((s) => {
                          const cat = s.category ?? "unknown";
                          const desc = s.description_zh || s.description || "";
                          return (
                            <li key={s.id} className="ws-skill-item">
                              <div className="ws-skill-row">
                                <span className={`ws-skill-badge ws-skill-badge-${cat}`}>
                                  {cat === "builtin" ? "内置" : cat === "agentic" ? "agentic" : cat}
                                </span>
                                <span className="ws-skill-name">{s.name}</span>
                                <button
                                  type="button"
                                  className="ws-skill-add-inline"
                                  disabled={skillBusy}
                                  onClick={() => addSkill(s.id)}
                                >
                                  ＋
                                </button>
                              </div>
                              {desc && <div className="ws-skill-desc">{shortDesc(desc)}</div>}
                            </li>
                          );
                        })}
                      </ul>
                    );
                  })()}
                </div>
              )}
            </div>
          </div>
        )}
        {activeRightTab === "conv" && (
          <div className="ws-conv-tab">
            <ConversationTab
              taskId={taskId}
              currentConvId={conversationId}
              canWrite={canWrite}
              reloadKey={convListReloadKey}
              onItemsLoaded={onConvItemsLoaded}
              onSelect={onConvSelect}
            />
          </div>
        )}
        {activeRightTab === "scheduled" && (
          <div className="ws-scheduled-tab" style={{ padding: "12px 14px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 10,
              }}
            >
              <span style={{ fontSize: 12, color: "var(--text-dim)", flex: 1 }}>
                本任务的定时执行（{scheduledItems.length}）
              </span>
              <button
                className="btn-ghost"
                style={{ fontSize: 11, padding: "2px 8px" }}
                onClick={() =>
                  navigate(`/scheduled-tasks?taskId=${encodeURIComponent(taskId)}&create=1`)
                }
                title="去定时任务全页管理"
              >
                管理 →
              </button>
            </div>
            {scheduledItems.length === 0 ? (
              <div className="ws-empty">
                本任务暂无定时。点「管理 →」新建。
              </div>
            ) : (
              <ul
                style={{
                  listStyle: "none",
                  padding: 0,
                  margin: 0,
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
                }}
              >
                {scheduledItems.map((s) => (
                  <li
                    key={s.id}
                    style={{
                      background: "var(--surface-2)",
                      border: "1px solid var(--border)",
                      borderRadius: 6,
                      padding: "8px 10px",
                      fontSize: 12,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                        marginBottom: 4,
                      }}
                    >
                      <span
                        style={{
                          fontSize: 10,
                          padding: "1px 6px",
                          borderRadius: 3,
                          background: s.enabled
                            ? "var(--success-dim)"
                            : "var(--surface-3)",
                          color: s.enabled
                            ? "var(--success)"
                            : "var(--text-muted)",
                        }}
                      >
                        {s.enabled ? "启用" : "停用"}
                      </span>
                      <span style={{ fontWeight: 500, flex: 1 }}>{s.name}</span>
                      <button
                        className="btn-ghost"
                        style={{ fontSize: 10, padding: "2px 6px" }}
                        disabled={!canWrite}
                        onClick={async () => {
                          try {
                            const r = await scheduledApi.runNow(s.task_id, s.id);
                            pushToast(
                              r.status === "failed" ? "error" : "success",
                              r.status === "failed"
                                ? `执行失败：${r.error?.message || "未知"}`
                                : "已立即执行",
                            );
                            await onReloadScheduled();
                          } catch (err) {
                            pushToast("error", (err as Error).message);
                          }
                        }}
                        title="立即执行一次"
                      >
                        ▶ 立即执行
                      </button>
                    </div>
                    <div
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: 11,
                        color: "var(--text-muted)",
                      }}
                    >
                      {s.cron}
                    </div>
                    {s.prompt && (
                      <div
                        style={{
                          fontSize: 11,
                          color: "var(--text-dim)",
                          marginTop: 4,
                          display: "-webkit-box",
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: "vertical",
                          overflow: "hidden",
                        }}
                      >
                        {s.prompt}
                      </div>
                    )}
                    {s.next_fire_at && (
                      <div
                        style={{
                          fontSize: 10,
                          color: "var(--text-muted)",
                          marginTop: 4,
                        }}
                      >
                        下次：{new Date(s.next_fire_at).toLocaleString()}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}
