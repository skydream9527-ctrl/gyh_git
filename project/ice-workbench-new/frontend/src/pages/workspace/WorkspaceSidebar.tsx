import type { RefObject } from "react";
import type { ChatInputRef } from "@/components/chat/ChatInput";
import { Skeleton } from "@/components/feedback/Skeleton";
import type { KBArticle, KBSummary } from "@/api/endpoints";
import type { AgentCard, FileMeta } from "@/types/api";
import { categorizeFile, fmtIcon, fmtSize, FILE_CATEGORY_DEFS } from "./utils";
import type { FileCategory } from "./utils";

export interface UploadItem {
  name: string;
  status: "pending" | "uploading" | "done" | "error";
  percent: number;
  message?: string;
}

export interface WorkspaceSidebarProps {
  taskId: string;
  files: FileMeta[];
  upload: { items: UploadItem[]; upload: (files: FileList | File[]) => void };
  fileGroupCollapsed: Record<FileCategory, boolean>;
  onFileGroupToggle: (key: FileCategory) => void;
  kbs: KBSummary[];
  expandedKbId: string | null;
  kbArticles: Record<string, KBArticle[]>;
  kbBusy: string | null;
  kbReferenced: Set<string>;
  activeFile: FileMeta | null;
  activeContent: string | null;
  agent: AgentCard | null;
  canWrite: boolean;
  isOwnerLike: boolean;
  chatInputRef: RefObject<ChatInputRef | null>;
  onOpenFile: (f: FileMeta) => void;
  onDownloadFile: (f: FileMeta) => void;
  onRemoveFile: (f: FileMeta) => void;
  onRefreshFile: (f: FileMeta) => Promise<void>;
  onToggleKb: (kb: KBSummary) => void;
  onReferenceKbArticle: (kb: KBSummary, a: KBArticle) => void;
  onCloseFilePreview: () => void;
  onOpenImport: () => void;
  pushToast: (type: "success" | "error" | "info", msg: string) => void;
}

export function WorkspaceSidebar({
  taskId: _taskId,
  files,
  upload,
  fileGroupCollapsed,
  onFileGroupToggle,
  kbs,
  expandedKbId,
  kbArticles,
  kbBusy,
  kbReferenced,
  activeFile,
  activeContent,
  agent,
  canWrite,
  isOwnerLike,
  chatInputRef,
  onOpenFile,
  onDownloadFile,
  onRemoveFile,
  onRefreshFile,
  onToggleKb,
  onReferenceKbArticle,
  onCloseFilePreview,
  onOpenImport,
  pushToast: _pushToast,
}: WorkspaceSidebarProps) {
  return (
    <aside className="ws-sidebar">
      <div className="ws-sb-section">
        <div className="ws-sb-head">
          <h3 className="v6-pane-title">Context & Data</h3>
          {canWrite && (
            <label className="ws-upload">
              + 上传
              <input
                type="file"
                multiple
                onChange={(e) => {
                  if (e.target.files) upload.upload(e.target.files);
                  e.target.value = "";
                }}
              />
            </label>
          )}
          {canWrite && (
            <button
              className="btn-ghost ws-import-btn"
              onClick={onOpenImport}
              title="从飞书文档 / 知识库链接导入文件"
            >
              🔗 导入链接
            </button>
          )}
        </div>
        {files.length === 0 && upload.items.length === 0 ? (
          <div className="ws-empty">还没有文件，拖拽或点击上传</div>
        ) : (
          <div className="ws-file-groups">
            {FILE_CATEGORY_DEFS.map((def) => {
              const groupFiles = files.filter((f) => categorizeFile(f) === def.key);
              if (groupFiles.length === 0) return null;
              const collapsed = fileGroupCollapsed[def.key];
              return (
                <div
                  key={def.key}
                  className={`ws-file-group${collapsed ? " is-collapsed" : ""}`}
                >
                  <button
                    type="button"
                    className="ws-file-group-head"
                    onClick={() => onFileGroupToggle(def.key)}
                    aria-expanded={!collapsed}
                  >
                    <span className="ws-fg-caret">{collapsed ? "▸" : "▾"}</span>
                    <span className="ws-fg-icon">{def.icon}</span>
                    <span className="ws-fg-label">{def.label}</span>
                    <span className="ws-fg-count">{groupFiles.length}</span>
                  </button>
                  {!collapsed && (
                    <ul className="ws-file-list">
                      {groupFiles.map((f) => {
                        const isImported = f.scope === "imported";
                        return (
                          <li key={f.id} onClick={() => onOpenFile(f)}>
                            <span
                              className="fl-icon"
                              title={isImported ? "已导入链接" : undefined}
                            >
                              {isImported ? "🔗" : fmtIcon(f.format)}
                            </span>
                            <span
                              className="fl-name"
                              title={isImported && f.source_url ? f.source_url : f.name}
                            >
                              {f.name}
                            </span>
                            <span className="fl-size">{fmtSize(f.size_bytes)}</span>
                            {isImported && (
                              <button
                                className="fl-refresh"
                                onClick={async (e) => {
                                  e.stopPropagation();
                                  await onRefreshFile(f);
                                }}
                                title="重新抓取最新内容"
                              >
                                ↻
                              </button>
                            )}
                            <button
                              className="fl-cite"
                              onClick={(e) => {
                                e.stopPropagation();
                                chatInputRef.current?.insertText(`@${f.name} `);
                                chatInputRef.current?.focus();
                              }}
                              title="引用到对话输入框"
                            >
                              📎
                            </button>
                            <button
                              className="fl-download"
                              onClick={(e) => {
                                e.stopPropagation();
                                onDownloadFile(f);
                              }}
                              title="下载到本地"
                            >
                              ⬇
                            </button>
                            {isOwnerLike && (
                              <button
                                className="fl-del"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onRemoveFile(f);
                                }}
                                title="删除"
                              >
                                ×
                              </button>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>
              );
            })}
            {upload.items.filter((u) => u.status !== "done").length > 0 && (
              <ul className="ws-file-list ws-upload-list">
                {upload.items
                  .filter((u) => u.status !== "done")
                  .map((u, i) => (
                    <li key={`u${i}`} className="ws-upload-row">
                      <span className="fl-icon">⏳</span>
                      <span className="fl-name">{u.name}</span>
                      <span className="fl-size">
                        {u.status === "uploading" ? `${u.percent}%` : u.message || "失败"}
                      </span>
                    </li>
                  ))}
              </ul>
            )}
          </div>
        )}
      </div>

      {/* 知识库：展开可引用文档到任务文件 */}
      <div className="ws-sb-section ws-sb-kb">
        <div className="ws-sb-head">
          <span>📚 知识库</span>
          <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: "auto" }}>
            {kbs.length} 个
          </span>
        </div>
        {kbs.length === 0 ? (
          <div className="ws-empty">暂无可用知识库</div>
        ) : (
          <ul className="ws-kb-list">
            {kbs.map((kb) => {
              const expanded = expandedKbId === kb.id;
              const arts = kbArticles[kb.id];
              const loading = kbBusy === kb.id;
              return (
                <li key={kb.id} className="ws-kb-item">
                  <button
                    type="button"
                    className="ws-kb-row"
                    onClick={() => onToggleKb(kb)}
                    title={kb.description || kb.name}
                  >
                    <span className="ws-kb-caret">{expanded ? "▾" : "▸"}</span>
                    <span className="ws-kb-icon">
                      {kb.source_type === "feishu_wiki" ? "🪶" : "📚"}
                    </span>
                    <span className="ws-kb-name">{kb.name}</span>
                    <span className="ws-kb-count">{kb.doc_count}</span>
                  </button>
                  {expanded && (
                    <div className="ws-kb-articles">
                      {loading && !arts ? (
                        <Skeleton lines={3} />
                      ) : !arts || arts.length === 0 ? (
                        <div className="ws-empty" style={{ padding: "6px 10px" }}>
                          暂无文档
                        </div>
                      ) : (
                        <ul>
                          {arts.map((a) => {
                            const busy = kbBusy === `${kb.id}:${a.id}`;
                            const referenced = kbReferenced.has(`${kb.id}:${a.id}`);
                            return (
                              <li key={a.id} className="ws-kb-article">
                                <span
                                  className="ws-kb-article-title"
                                  title={a.title}
                                >
                                  {a.title}
                                </span>
                                {canWrite && (
                                  <button
                                    type="button"
                                    className={`ws-kb-refbtn${referenced ? " is-referenced" : ""}`}
                                    disabled={busy || referenced}
                                    onClick={() => onReferenceKbArticle(kb, a)}
                                    title={referenced ? "已引用到任务文件" : "引用到任务文件"}
                                  >
                                    {busy ? "…" : referenced ? "✓ 已引用" : "引用"}
                                  </button>
                                )}
                              </li>
                            );
                          })}
                        </ul>
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* 文件预览：点击左侧列表后在这里显示内容 */}
      {activeFile && (
        <div className="ws-sb-section ws-sb-filepreview">
          <div className="ws-sb-head">
            <span className="ws-file-name" title={activeFile.name}>
              {fmtIcon(activeFile.format)} {activeFile.name}
            </span>
            <button
              className="btn-ghost ws-sb-filepreview-close"
              onClick={onCloseFilePreview}
              title="关闭预览"
            >
              ×
            </button>
          </div>
          {activeContent === null ? (
            <Skeleton lines={5} />
          ) : (
            <pre className="ws-file-pre">{activeContent}</pre>
          )}
        </div>
      )}

      {/* V6: Running Agents Section */}
      <div className="ws-sb-section v6-agents-section">
        <h3 className="ws-sb-head" style={{ marginBottom: 12 }}>运行智能体组合</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {agent ? (
            <div style={{ display: "flex", alignItems: "center", gap: 12, padding: 8, borderRadius: 8, background: "var(--surface)", border: "1px solid var(--border)", boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)" }}>
              <div style={{ width: 32, height: 32, borderRadius: 4, background: "var(--accent-soft)", color: "var(--accent-text)", display: "flex", alignItems: "center", justifyContent: "center", border: "1px solid var(--accent-soft)", fontSize: 18 }}>{agent.icon || "🤖"}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text)", display: "flex", alignItems: "center", gap: 4 }}>{agent.name} <span style={{ background: "var(--surface-2)", fontSize: 9, padding: "2px 4px", borderRadius: 4, border: "1px solid var(--border)" }}>主控</span></div>
                <div style={{ fontSize: 10, color: "var(--text-muted)" }}>{agent.paradigm}</div>
              </div>
            </div>
          ) : (
            <div className="ws-empty">尚未绑定 Agent</div>
          )}
          {/* Optional secondary agent placeholder just for v6 visuals if wanted */}
          {agent && (
            <div style={{ display: "flex", alignItems: "center", gap: 12, padding: 8, borderRadius: 8, background: "var(--surface)", border: "1px solid var(--border)", boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)", opacity: 0.6 }}>
              <div style={{ width: 32, height: 32, borderRadius: 4, background: "var(--p-gray-soft)", color: "var(--p-gray)", display: "flex", alignItems: "center", justifyContent: "center", border: "1px solid var(--p-gray-soft)", fontSize: 18 }}>📊</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text)" }}>Data Analyst</div>
                <div style={{ fontSize: 10, color: "var(--text-muted)" }}>数据分析与处理</div>
              </div>
            </div>
          )}
        </div>
      </div>

    </aside>
  );
}
