/* ICE-DATA-WORK 原型外壳：注入侧栏 / 顶栏 / Twin Dock / 抽屉。
   每个页面在 <body data-page="..." data-title="..."> 上声明所属导航与标题。 */
(function () {
  var NAV = [
    { group: "Operate", items: [
      { page: "workbench",   label: "Workbench",      icon: "⌂", href: "workbench.html" },
      { page: "new-mission", label: "新建任务",        icon: "＋", href: "new-mission.html" },
      { page: "board",       label: "任务看板",        icon: "▤", href: "board.html" }
    ]},
    { group: "Workspace", items: [
      { page: "workspace-data",    label: "数据分析工作台", icon: "▦", href: "workspace-data.html" },
      { page: "workspace-general", label: "通用工作台",     icon: "▣", href: "workspace-general.html" }
    ]},
    { group: "Assets", items: [
      { page: "agents",    label: "Agent Hub",   icon: "◎", href: "agents.html" },
      { page: "knowledge", label: "知识与产物",   icon: "◩", href: "knowledge.html" },
      { page: "project",   label: "项目空间",     icon: "◇", href: "project.html" },
      { page: "team",      label: "团队空间",     icon: "⬡", href: "team.html" }
    ]},
    { group: "Control", items: [
      { page: "twin",      label: "数字分身管理", icon: "☉", href: "twin.html" },
      { page: "approvals", label: "审批与审计",   icon: "☷", href: "approvals.html" },
      { page: "admin",     label: "管理后台",     icon: "⚙", href: "admin.html" }
    ]}
  ];

  var side = document.getElementById("side");
  var top = document.getElementById("top");
  var dock = document.getElementById("dock");
  if (!side) return; // login / index 等独立页无外壳

  var active = document.body.dataset.page || "";
  var title = document.body.dataset.title || "Workbench";

  /* ---------- Sidebar ---------- */
  var navHtml = "";
  NAV.forEach(function (g) {
    navHtml += '<div class="nav-label">' + g.group + "</div>";
    g.items.forEach(function (it) {
      var cls = "nav-btn" + (it.page === active ? " active" : "");
      navHtml += '<a class="' + cls + '" href="' + it.href + '"><span class="icon">' + it.icon + "</span>" + it.label + "</a>";
    });
  });
  side.innerHTML =
    '<a class="brand" href="workbench.html"><div class="brand-mark">IDW</div><div><strong>ICE-DATA-WORK</strong><span>User → Twin → Agents</span></div></a>' +
    '<div class="switcher"><label>Team / Project</label>' +
      '<select id="teamSel"><option>增长数据团队</option><option>风控数据团队</option><option>我的个人项目</option></select>' +
      '<select id="projSel"><option>p_growth · 增长分析</option><option>p_retention · 留存</option><option>p_personal · 个人项目</option></select>' +
    "</div>" +
    '<nav class="nav" aria-label="Navigation">' + navHtml + "</nav>" +
    '<div class="side-card">Workbench 展示运行内容；点任务/文档/Agent 进入 Workspace；右侧 Wisdom Twin 始终在场。</div>';

  /* ---------- Topbar ---------- */
  if (top) {
    top.className = "topbar";
    top.innerHTML =
      '<div class="command"><div class="command-left"><kbd>⌘ K</kbd><span>把目标交给你的 Wisdom Twin；高风险动作必须你确认。</span></div>' +
      '<a class="btn primary" href="new-mission.html">交给分身</a></div>';
  }

  /* ---------- Twin Dock ---------- */
  if (dock) {
    dock.className = "dock";
    dock.innerHTML =
      '<div class="dock-inner">' +
      '<div class="dock-card"><div class="dock-head"><div class="dock-title"><div><strong>Wisdom Twin · 我的分身</strong><span>当前页面：<b>' + title + '</b> · 项目：<b id="dockProj">p_growth</b></span></div><span class="pill blue">L3 Request</span></div></div>' +
        '<div class="dock-chat">' +
          '<div class="dock-msg twin">我始终在右侧，维护上下文、协调其他 Agent，并把高风险动作交给你确认。</div>' +
          '<div class="dock-msg me">这次先把 DAU 归因推进完。</div>' +
          '<div class="dock-msg twin">好。Data Agent 已在任务里，报告草稿 v0.7 完成，待你确认是否补查 ANR。</div>' +
        "</div>" +
        '<div class="dock-input"><input id="twinCmd" placeholder="对分身说：带我去看板…" /><button class="btn primary" id="twinSend">Send</button></div>' +
        '<div style="display:flex;flex-wrap:wrap;gap:6px;padding:2px 12px 12px"><span class="subtle" style="font-size:11px;width:100%">快捷指令（D-12 导航）：</span><span class="pill slate idw-nav" data-go="workbench.html" style="cursor:pointer">Workbench</span><span class="pill slate idw-nav" data-go="board.html" style="cursor:pointer">看板</span><span class="pill slate idw-nav" data-go="workspace-data.html" style="cursor:pointer">数据分析</span><span class="pill slate idw-nav" data-go="approvals.html" style="cursor:pointer">审批</span></div></div>' +
      '<div class="dock-section"><h3>数字分身建议</h3><div class="suggestion"><strong>建议：补查 ANR 与低端机型</strong><p>可解释占比可从 72% 提升到约 85%。</p><div class="actions"><a class="btn primary sm" href="workspace-data.html">继续计划</a><button class="btn sm">稍后</button></div></div></div>' +
      '<div class="dock-section"><h3>待你确认</h3><div class="confirm-card"><strong>允许 Data Agent 补查 ANR？</strong><p>只读查询，预计 12k tokens。</p><div class="actions"><a class="btn primary sm" href="approvals.html">确认</a><button class="btn sm">修改</button><button class="btn danger sm">拒绝</button></div></div>' +
        '<div class="memory-card" style="margin-top:10px"><strong>记忆候选：表格优先</strong><p>晋升到 →</p><div class="seg"><label><input type="radio" name="mscope" checked>个人偏好</label><label><input type="radio" name="mscope">项目</label><label><input type="radio" name="mscope">团队</label><label><input type="radio" name="mscope">贡献给该 Agent</label></div><div class="actions"><a class="btn primary sm" href="approvals.html">确认晋升</a></div></div></div>' +
      "</div>";
    var ts = document.getElementById("teamSel"), ps = document.getElementById("projSel"), dp = document.getElementById("dockProj");
    if (ps && dp) ps.addEventListener("change", function () { dp.textContent = ps.value.split(" ")[0]; });
  }

  /* ---------- Drawer ---------- */
  var DRAWER = {
    status: { title: "状态 / 任务", html: '<div class="drawer-section"><strong>状态 / 任务</strong><p>Workbench 汇总运行内容；Workspace 展示当前任务阶段、进度、阻塞点与待确认动作。</p></div><div class="mini-list"><div class="mini-row"><div><strong>当前阶段</strong><span>报告草稿 v0.7</span></div><span class="pill blue">Step 3</span></div><div class="mini-row"><div><strong>待确认</strong><span>是否补查 ANR</span></div><span class="pill amber">Waiting</span></div></div>' },
    agents: { title: "参与者状态", html: '<div class="drawer-section"><strong>本任务参与者</strong><p>每个参与者：当前状态 · 核心能力 · 正在做。</p></div><div class="mini-list"><div class="mini-row"><div><strong>我的 Twin · 工作中</strong><span>编排协调 / 上下文 · 正在：汇总结果并请求确认</span></div><span class="pill blue">L3</span></div><div class="mini-row"><div><strong>Data Agent · 工作中</strong><span>SQL 查询与归因 · 正在：执行 kyuubi_query（2/3）</span></div><span class="pill green">L2</span></div></div>' },
    files: { title: "文件 / 数据", html: '<div class="drawer-section"><strong>任务文件区</strong><p>tasks/&lt;tid&gt;/files —— 任务独立文件空间，不跨任务。</p></div><div class="mini-list"><div class="mini-row"><div><strong>analysis_report_v07.md</strong><span>output · 报告草稿</span></div><span class="pill green">Report</span></div><div class="mini-row"><div><strong>dau_trend.csv</strong><span>output · 查询结果</span></div><span class="pill amber">Data</span></div></div>' },
    conversations: { title: "对话列表", html: '<div class="drawer-section"><strong>对话列表</strong><p>当前对话在主视图，历史对话默认隐藏。</p></div><div class="mini-list"><div class="mini-row"><div><strong>DAU 归因（当前）</strong><span>我 + Twin + Data Agent</span></div><span class="pill blue">Current</span></div></div>' },
    timeline: { title: "执行记录", html: '<div class="drawer-section"><strong>执行记录 / 审计</strong><p>工具调用、确认请求、记忆晋升均进时间线。</p></div><div class="mini-list"><div class="mini-row"><div><strong>kyuubi_query</strong><span>只读 · 14,238 行</span></div><span class="pill green">Done</span></div><div class="mini-row"><div><strong>补查 ANR</strong><span>等待确认</span></div><span class="pill amber">Pending</span></div></div>' },
    artifacts: { title: "产物列表", html: '<div class="drawer-section"><strong>产物列表（渐进展开）</strong><p>点单条查看内容；状态：草稿 / 已确认 / 已发布。</p></div><div class="mini-list"><div class="mini-row"><div><strong>DAU 下滑归因报告 v0.7</strong><span>报告 · 项目级 · 刚刚</span></div><span class="pill amber">草稿</span></div><div class="mini-row"><div><strong>dau_trend.csv</strong><span>数据 · 任务级</span></div><span class="pill green">已确认</span></div><div class="mini-row"><div><strong>口径定义：DAU/留存</strong><span>文档 · 项目级</span></div><span class="pill blue">已发布</span></div></div>' }
  };
  var backdrop = document.createElement("div"); backdrop.className = "drawer-backdrop";
  var drawer = document.createElement("aside"); drawer.className = "drawer";
  drawer.innerHTML = '<div class="drawer-head"><div><h2 id="dwTitle">详情</h2><p class="subtle">非核心信息通过抽屉展示。</p></div><button class="btn" id="dwClose">关闭</button></div><div class="drawer-body" id="dwBody"></div>';
  document.body.appendChild(backdrop); document.body.appendChild(drawer);
  function openDrawer(name) {
    var d = DRAWER[name]; if (!d) return;
    document.getElementById("dwTitle").textContent = d.title;
    document.getElementById("dwBody").innerHTML = d.html;
    drawer.classList.add("open"); backdrop.classList.add("open");
    document.querySelectorAll("[data-drawer]").forEach(function (b) { b.classList.toggle("drawer-active", b.dataset.drawer === name); });
  }
  function closeDrawer() { drawer.classList.remove("open"); backdrop.classList.remove("open"); document.querySelectorAll("[data-drawer]").forEach(function (b) { b.classList.remove("drawer-active"); }); }
  document.querySelectorAll("[data-drawer]").forEach(function (b) { b.addEventListener("click", function () { openDrawer(b.dataset.drawer); }); });
  document.getElementById("dwClose").addEventListener("click", closeDrawer);
  backdrop.addEventListener("click", closeDrawer);
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeDrawer(); });

  /* ---------- Modal（邀请参与者 / 授权他人 Twin，P2-02） ---------- */
  var MODAL = {
    "invite-twin": {
      title: "邀请参与者协作",
      sub: "工具 Agent / 我的 Twin 可直接加入；他人的数字分身需其管理员授权（二期 P2-02）",
      body:
        '<div class="seg-tabs" id="inviteTabs">' +
          '<span class="seg-tab" data-pane="tool">工具 Agent</span>' +
          '<span class="seg-tab" data-pane="mytwin">我的 Twin</span>' +
          '<span class="seg-tab active" data-pane="othertwin">他人的数字分身 ⭐</span>' +
        '</div>' +
        '<div class="pane" data-pane="tool" hidden>' +
          '<div class="form-row"><span class="lbl">选择工具 Agent（团队共享，直接加入，无需授权）</span>' +
          '<select><option>Data Agent · L2 只读</option><option>波动归因 Agent · L2</option><option>AB 实验 Agent · L2</option></select></div>' +
          '<div class="actions" style="margin-top:12px"><button class="btn primary" data-modal-close>加入任务</button></div>' +
        '</div>' +
        '<div class="pane" data-pane="mytwin" hidden>' +
          '<div class="note blue">我的 Twin 默认随我进入每个任务并常驻右侧。此处可确认其在本任务的权限等级。</div>' +
          '<div class="form-row" style="margin-top:10px"><span class="lbl">本任务权限等级</span><select><option>L3 Request（默认）</option><option>L2 Delegate Draft</option><option>L1 Suggest</option></select></div>' +
          '<div class="actions" style="margin-top:12px"><button class="btn primary" data-modal-close>确认在场</button></div>' +
        '</div>' +
        '<div class="pane" data-pane="othertwin">' +
          '<div class="form-row"><span class="lbl">选择同事的数字分身</span>' +
          '<select id="visitorTwin"><option>张敏的分身（增长数据团队）</option><option>李航的分身（增长数据团队）</option><option>刘工的分身（风控数据团队）</option></select></div>' +
          '<div class="form-row"><span class="lbl">授权范围 · scoped grant</span>' +
            '<label class="check"><input type="checkbox" checked disabled> 限定任务：仅本任务「DAU 下滑归因」</label>' +
            '<label class="check"><input type="checkbox" checked> 只读宿主空间（不可读我的用户/Agent 私有记忆）</label>' +
            '<label class="check"><input type="checkbox" checked> 仅可写本任务空间，贡献带来源标注</label>' +
            '<label class="check"><input type="checkbox" checked> 可随时撤销授权</label>' +
          '</div>' +
          '<div class="form-row"><span class="lbl">有效期</span><select><option>任务结束自动失效</option><option>7 天</option><option>自定义…</option></select></div>' +
          '<div class="note amber">授权链：需对方分身的<b>管理员批准</b>后才生效。</div>' +
          '<div class="note violet">记忆回流：访客分身产生的记忆回流到<b>它自己 owner 的空间</b>，受对方审批，不进我的空间。</div>' +
          '<div class="note blue">审计：跨用户协作全程双方可见，可随时在「审批与审计」撤销。</div>' +
        '</div>',
      foot: '<button class="btn" data-modal-close>取消</button><button class="btn primary" id="sendGrant">发送授权请求</button>'
    },
    "contribute-skill": {
      title: "贡献为 Skill / 更新 Agent",
      sub: "把跑通的代码沉淀为可复用 Skill，并让 Agent 学会何时使用（D-13）",
      body:
        '<div class="form-row"><span class="lbl">名称</span><input value="XX 业务 DAU 查询" /></div>' +
        '<div class="form-row"><span class="lbl">描述</span><input value="按业务线/渠道/日期查询 XX 业务 DAU" /></div>' +
        '<div class="form-row"><span class="lbl">运行时</span><select><option>SQL（kyuubi 只读）</option><option>Python（沙盒）</option></select></div>' +
        '<div class="form-row"><span class="lbl">代码（来自本次贡献，沙盒已跑通）</span><pre style="margin:0;padding:11px;background:#0d1117;color:#c9d1d9;border-radius:12px;overflow:auto;font-family:var(--mono);font-size:12px;line-height:1.5">SELECT dt, channel, count(distinct uid) dau\nFROM biz_xx.user_active\nWHERE dt BETWEEN :date_start AND :date_end\nGROUP BY dt, channel</pre></div>' +
        '<div class="form-row"><span class="lbl">入参 schema（自动抽取）</span><div class="seg"><span class="pill slate">date_range</span><span class="pill slate">channel?</span></div></div>' +
        '<div class="form-row"><span class="lbl">沉淀范围（D-06）</span>' +
          '<label class="check"><input type="radio" name="skscope" checked> 个人草稿 Skill（仅我可用，立即生效，低风险）</label>' +
          '<label class="check"><input type="radio" name="skscope"> 贡献给团队 Skill（需沙盒 test-run 通过 + 审核）</label>' +
        '</div>' +
        '<label class="check"><input type="checkbox" checked> 绑定到 Data Agent：写 knowledge「查 XX 业务 DAU 时用此 Skill」，Agent 版本 +1</label>' +
        '<label class="check"><input type="checkbox"> 同时生成一条 Memory（口径/经验）</label>',
      foot: '<button class="btn" data-modal-close>取消</button><button class="btn primary" id="sendSkill">沉淀为 Skill</button>'
    }
  };
  var mBackdrop = document.createElement("div");
  mBackdrop.className = "modal-backdrop";
  mBackdrop.innerHTML = '<div class="modal"><div class="modal-head"><div><h2 id="mTitle"></h2><p id="mSub"></p></div><button class="btn sm" data-modal-close>✕</button></div><div class="modal-body" id="mBody"></div><div class="modal-foot" id="mFoot"></div></div>';
  document.body.appendChild(mBackdrop);
  var mTitle = mBackdrop.querySelector("#mTitle"), mSub = mBackdrop.querySelector("#mSub"), mBody = mBackdrop.querySelector("#mBody"), mFoot = mBackdrop.querySelector("#mFoot");
  function bindModalClose() { mBackdrop.querySelectorAll("[data-modal-close]").forEach(function (b) { b.addEventListener("click", closeModal); }); }
  function openModal(name) {
    var m = MODAL[name]; if (!m) return;
    mTitle.textContent = m.title; mSub.textContent = m.sub; mBody.innerHTML = m.body; mFoot.innerHTML = m.foot;
    mBackdrop.classList.add("open");
    bindModalClose();
    // tab 切换
    mBody.querySelectorAll("#inviteTabs .seg-tab").forEach(function (t) {
      t.addEventListener("click", function () {
        mBody.querySelectorAll("#inviteTabs .seg-tab").forEach(function (x) { x.classList.remove("active"); });
        t.classList.add("active");
        var p = t.dataset.pane;
        mBody.querySelectorAll(".pane").forEach(function (pane) { pane.hidden = (pane.dataset.pane !== p); });
        mFoot.style.display = (p === "othertwin") ? "flex" : "none";
      });
    });
    // 发送授权请求 → 切到等待审批状态
    var sg = mBody.parentNode.querySelector("#sendGrant");
    if (sg) sg.addEventListener("click", function () {
      var who = (mBody.querySelector("#visitorTwin") || {}).value || "对方分身";
      mTitle.textContent = "授权请求已发送";
      mSub.textContent = "等待对方管理员批准";
      mBody.innerHTML = '<div class="note green">✓ 已向「' + who + '」的管理员发送授权请求。</div>' +
        '<div class="note blue">批准后，该分身将作为新参与者加入本任务对话，发言与产出均带来源标注；其记忆回流到对方空间。</div>' +
        '<div class="actions" style="margin-top:6px"><a class="btn" href="approvals.html">在审批与审计中查看</a></div>';
      mFoot.innerHTML = '<button class="btn primary" data-modal-close>完成</button>';
      bindModalClose();
    });
    var ss = mBody.parentNode.querySelector("#sendSkill");
    if (ss) ss.addEventListener("click", function () {
      var checked = mBody.querySelector('input[name=skscope]:checked');
      var team = checked && /团队/.test(checked.parentNode.textContent);
      mTitle.textContent = "已沉淀为 Skill";
      mSub.textContent = team ? "已提交团队审核" : "个人草稿，立即可用";
      mBody.innerHTML = '<div class="note green">✓ 已沉淀为' + (team ? "团队候选" : "个人草稿") + ' Skill「XX 业务 DAU 查询」v1，并绑定 Data Agent（版本 +1）。</div>' +
        (team
          ? '<div class="note amber">已进入审核中心：需沙盒 test-run 通过 + owner/admin 审核后，全团队的 Data Agent 才会学会。</div>'
          : '<div class="note blue">下次你问"查 XX 业务 DAU"，Data Agent 会直接调用，无需再贴代码。可随时在 Agent 详情里"贡献给团队"。</div>') +
        '<div class="actions" style="margin-top:6px"><a class="btn" href="agent-detail.html">查看 Data Agent 的 Skills</a></div>';
      mFoot.innerHTML = '<button class="btn primary" data-modal-close>完成</button>';
      bindModalClose();
    });
  }
  function closeModal() { mBackdrop.classList.remove("open"); }
  document.querySelectorAll("[data-modal]").forEach(function (b) { b.addEventListener("click", function () { openModal(b.dataset.modal); }); });
  mBackdrop.addEventListener("click", function (e) { if (e.target === mBackdrop) closeModal(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeModal(); });

  /* ---------- D-12 Twin 导航感知与控制 ---------- */
  var GO = [
    { k: ["workbench", "回工作台", "主页", "首页"], href: "workbench.html" },
    { k: ["看板", "board", "任务板"], href: "board.html" },
    { k: ["新建", "建任务", "new mission"], href: "new-mission.html" },
    { k: ["数据分析", "分析工作台", "data"], href: "workspace-data.html" },
    { k: ["通用工作台", "文档工作台", "general"], href: "workspace-general.html" },
    { k: ["agent", "工具"], href: "agents.html" },
    { k: ["知识", "产物", "knowledge"], href: "knowledge.html" },
    { k: ["项目"], href: "project.html" },
    { k: ["团队"], href: "team.html" },
    { k: ["分身", "twin"], href: "twin.html" },
    { k: ["审批", "审计", "approval"], href: "approvals.html" },
    { k: ["管理", "后台", "admin"], href: "admin.html" }
  ];
  function twinNavigate(text) {
    var t = (text || "").toLowerCase();
    for (var i = 0; i < GO.length; i++) for (var j = 0; j < GO[i].k.length; j++) {
      if (t.indexOf(GO[i].k[j]) >= 0) { location.href = GO[i].href; return true; }
    }
    return false;
  }
  var cmd = document.getElementById("twinCmd"), send = document.getElementById("twinSend");
  function runCmd() { var v = (cmd.value || "").trim(); if (!v) return; if (!twinNavigate(v)) { cmd.value = ""; cmd.placeholder = '没听懂目的地，试试"带我去看板"'; } }
  if (send) send.addEventListener("click", runCmd);
  if (cmd) cmd.addEventListener("keydown", function (e) { if (e.key === "Enter") runCmd(); });
  document.querySelectorAll(".idw-nav").forEach(function (c) { c.addEventListener("click", function () { location.href = c.dataset.go; }); });
})();
