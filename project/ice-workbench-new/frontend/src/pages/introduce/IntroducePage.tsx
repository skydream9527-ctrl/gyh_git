import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { agentApi } from "@/api/endpoints";
import type { AgentCard } from "@/types/api";
import { ThemeSelect } from "@/components/shell/ThemeSelect";
import "./Introduce.css";

const PARADIGM_DESC: Record<string, string> = {
  biz: "经营数据拆解归因与趋势洞察",
  ab: "AB 实验显著性检验、样本均衡、效应量评估",
  wave: "多维下钻指标异常根因定位",
  data: "自然语言生成 SQL 查询，自动可视化",
  gray: "灰度版本对比与放量决策建议",
};

export function IntroducePage() {
  const [agents, setAgents] = useState<AgentCard[]>([]);

  useEffect(() => {
    agentApi.list().then((r) => setAgents(r.items)).catch(() => {});
  }, []);

  return (
    <div className="intro-page">
      <div className="intro-bg-grid" />
      <div className="intro-orb intro-orb-1" />
      <div className="intro-orb intro-orb-2" />

      <nav className="intro-nav">
        <Link to="/" className="brand">
          <div className="brand-logo">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="var(--primary-on)" strokeWidth="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z" />
              <path d="M2 17l10 5 10-5" />
              <path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <span className="brand-name">
            <span className="brand-accent">ICE</span> Data Workbench
          </span>
        </Link>
        <div className="intro-nav-links">
          <a href="#concepts">核心概念</a>
          <a href="#cases">实际案例</a>
          <a href="#features">功能特性</a>
        </div>
        <div className="intro-nav-actions">
          <ThemeSelect />
          <Link to="/login" className="cta-nav">
            立即体验 →
          </Link>
        </div>
      </nav>

      <main className="intro-container">
        <section className="intro-hero">
        <span className="intro-tag">ICE v6 全新发布</span>
          <h1>
            基于 <span className="intro-accent">多智能体协同</span> 的
            <br />
            数据工作舱
          </h1>
          <p>
            告别脆弱的一问一答脚本。ICE v6 引入子智能体调度网络、Human-in-the-loop 人工介入和飞书活数据挂载，让数据清洗、归因分析到报告推送形成可监控的企业级工作流。
          </p>
          <div className="intro-cta-row">
            <Link to="/login" className="btn-primary intro-cta">
              立即体验 →
            </Link>
            <Link to="/guide" className="btn-secondary intro-cta">
              查看使用指南
            </Link>
          </div>
          <div className="intro-stats">
            <div>
              <div className="num">{agents.length || 5}</div>
              <div className="label">智能 Agent</div>
            </div>
            <div>
              <div className="num">3</div>
              <div className="label">本地 Skills</div>
            </div>
            <div>
              <div className="num">5</div>
              <div className="label">工作范式</div>
            </div>
            <div>
              <div className="num">2</div>
              <div className="label">登录方式</div>
            </div>
          </div>
        </section>

        <section className="intro-section" id="concepts">
          <h2>核心概念</h2>
          <div className="intro-concept-grid">
            <Concept icon="▦" name="Multi-Agent 工作流" desc="Planner 拆解目标，数据分析、检索、报告节点分工执行" />
            <Concept icon="!" name="Human-in-the-loop" desc="发现异常或高危操作时自动挂起，等待人工确认后继续" />
            <Concept icon="↯" name="异步后台运行" desc="解绑浏览器连接，关掉页面后仍可跑批并通过通知回捞" />
            <Concept icon="◎" name="飞书活数据挂载" desc="多维表格、Wiki、文档可作为任务上下文随取随用" />
            <Concept icon="⏱" name="Cron 调度转化" desc="手动跑通的 Workspace 可一键绑定定时调度" />
            <Concept icon="▤" name="执行计划可视化" desc="右侧执行树展示每个子节点的状态、耗时和阻塞原因" />
          </div>
        </section>

        <section className="intro-section" id="cases">
          <h2>实际案例</h2>
          <div className="intro-case-grid">
            {agents.slice(0, 4).map((a) => (
              <Link key={a.id} to="/login" className="intro-case-card">
                <div className="intro-case-icon">{a.icon}</div>
                <div className="intro-case-name">{a.name}</div>
                <div className="intro-case-desc">{a.description || PARADIGM_DESC[a.paradigm]}</div>
                <span className="intro-case-cta">用此 Agent 创建 →</span>
              </Link>
            ))}
            {agents.length === 0 &&
              Object.entries(PARADIGM_DESC)
                .slice(0, 4)
                .map(([k, v]) => (
                  <Link key={k} to="/login" className="intro-case-card">
                    <div className="intro-case-name">{k}</div>
                    <div className="intro-case-desc">{v}</div>
                  </Link>
                ))}
          </div>
        </section>

        <section className="intro-section" id="features">
          <h2>覆盖完整功能</h2>
          <div className="intro-feat-grid">
            <Feature n="01" title="三栏数据工作台" desc="Context & Data / Chat & Action / Execution Plan" />
            <Feature n="02" title="富交互审批卡片" desc="表格、输入框、确认按钮承接人工介入流程" />
            <Feature n="03" title="Agent 编排拓扑" desc="可视化配置 Planner 与下游执行节点关系" />
            <Feature n="04" title="后台运行与通知" desc="异步任务集中展示进度，挂起时回到待处理队列" />
            <Feature n="05" title="定时调度大盘" desc="cron + Agent 自动执行 + 飞书 / 文件交付" />
            <Feature n="06" title="治理与成本管理" desc="用户、Agent、用量、审计和系统配置统一管理" />
          </div>
        </section>
      </main>

      <footer className="intro-footer">ICE Data Workbench v6 · Multi-Agent Data Workspace</footer>
    </div>
  );
}

function Concept({ icon, name, desc }: { icon: string; name: string; desc: string }) {
  return (
    <div className="intro-concept">
      <div className="intro-concept-icon">{icon}</div>
      <div className="intro-concept-name">{name}</div>
      <div className="intro-concept-desc">{desc}</div>
    </div>
  );
}

function Feature({ n, title, desc }: { n: string; title: string; desc: string }) {
  return (
    <div className="intro-feat">
      <div className="intro-feat-num">{n}</div>
      <div>
        <div className="intro-feat-title">{title}</div>
        <div className="intro-feat-desc">{desc}</div>
      </div>
    </div>
  );
}
