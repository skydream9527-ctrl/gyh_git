# 如何设置 `$MIFY_API_KEY`

Mify skill 的所有脚本都从环境变量 `$MIFY_API_KEY` 读取 token。下面列了**最推荐的方式 0**（让 Claude 帮你一键装）和几种手动后备方式。

## 前置：拿到 token

Mify 的 API key 需要到内部 Mify 控制台申请。如果你没有，问你所在小组的 Mify 对接人，或在「小米 AI 生产力平台」相关飞书群里提个工单。格式形如 `sk-XXXXXXXXX...`（约 50 字符）。

拿到后选下面任一方式安装。

---

## 方式 0：让 Claude 帮你装（最推荐）

直接在任意 Claude Code 对话里贴出 token，类似：

> 帮我把这个 Mify key 装好：`sk-你的token`

本 skill 的触发词覆盖了这种场景 —— Claude 会自动调用 `scripts/install_token.py`，后者会：

1. 校验 key 格式
2. 对 `/v1/models` 实测一次，验证 key 确实能用
3. 写入 `~/.config/mify/credentials`（chmod 600，覆盖旧值）
4. 在 `~/.zshrc` / `~/.bashrc` 里追加 source 语句（幂等，已有不重复）
5. 报告每步结果（不会 echo token 本身）

然后开新终端或 `source ~/.config/mify/credentials` 立即生效，完事。

**手动等价命令**（若你想绕过 Claude 直接跑）：

```bash
printf %s 'sk-你的token' | python3 ~/.claude/skills/mify-model-gateway/scripts/install_token.py
```

> 用 `printf %s` 和**单引号**，不要用 `echo "..."`。反斜杠、`$`、反引号、`!` 都可能在 `echo`/双引号下出问题。

---

## 方式 1：一次性（只在当前 shell 会话生效）

最简单，适合临时用：

```bash
export MIFY_API_KEY=sk-你的token
```

关掉终端就没了。适合脚本短暂 demo 或共享机器上临时操作。

---

## 方式 2：独立 secrets 文件 + zshrc/bashrc source（推荐）

Token 放在专属文件里，`chmod 600` 只有你本人可读，不会被 dotfiles git 仓库或同步工具误带走：

**a. 创建目录和文件：**

```bash
mkdir -p ~/.config/mify && chmod 700 ~/.config/mify

cat > ~/.config/mify/credentials <<'EOF'
# Mify 大模型网关 API Key
export MIFY_API_KEY=sk-你的token
EOF

chmod 600 ~/.config/mify/credentials
```

**b. 在 shell 启动文件里 source 它：**

zsh 用户（macOS 默认）：

```bash
cat >> ~/.zshrc <<'EOF'

# Mify 大模型网关凭据
[ -r "$HOME/.config/mify/credentials" ] && source "$HOME/.config/mify/credentials"
EOF
```

bash 用户把 `~/.zshrc` 换成 `~/.bashrc`（Linux）或 `~/.bash_profile`（macOS 老 bash）。

**c. 让当前终端立即生效（或开新终端）：**

```bash
source ~/.zshrc
```

**验证：**

```bash
echo "len=${#MIFY_API_KEY}, prefix=${MIFY_API_KEY:0:8}..."
# 期望输出：len=50 左右, prefix=sk-XXXXX
```

### 吊销 / 更换 token

就改一个文件：

```bash
vi ~/.config/mify/credentials   # 改 export 那一行
source ~/.zshrc                 # 或者开新终端
```

### 和 git 的关系

如果你把 `~/.zshrc` 放进 dotfiles 仓库（很多开发者会这么做），这套方案天然安全：
- `~/.zshrc` 里只有 `source` 指令，**不含 token**，可以安全提交。
- `~/.config/mify/credentials` 不在仓库里，token 不外泄。

---

## 方式 3：直接 export 到 ~/.zshrc（不推荐）

```bash
echo 'export MIFY_API_KEY=sk-你的token' >> ~/.zshrc
source ~/.zshrc
```

能用但有两个风险：

1. 如果 `~/.zshrc` 进了 dotfiles git 仓库，token 会被提交上去。
2. 共享 / 调试 shell 配置时容易误贴出来。

只在**临时个人机**且不同步 dotfiles 的情况下用。

---

## 对 Claude / subagent 执行 skill 脚本的意义

Claude Code 调用本 skill 的 Bash 工具时，如果你的 shell 已经 export 了 `$MIFY_API_KEY`（方式 2/3 都可以），脚本会自动拿到；但 Claude 的每个 Bash 调用是**独立子 shell**，env 默认继承自父进程。

- **Claude Code CLI 本身**：启动时继承了你 login shell 的 env，所以方式 2 配好后再开 Claude Code，后续 bash 调用就有 token。
- **Agent / subagent**：它们的 bash 会继承父进程 env，所以同样没问题。

如果你验证 skill 脚本说「Missing $MIFY_API_KEY」，先在 Claude 的对话里让它跑：

```bash
echo "MIFY_API_KEY len=${#MIFY_API_KEY}"
```

确认 env 有没有传过来。如果没有，说明你是在 **Claude Code 启动之前** 配置的方式 2 还没生效 —— 重启一次 Claude Code 即可。

---

## 安全底线

以下是**绝对不要做**的事：

- ❌ 把 token 写进 SKILL.md、scripts/、references/、或 skill 目录里任何文件。Skill 是可能被打包分发的。
- ❌ 把 token 写到项目源码、commit message、PR 描述、issue 评论里。
- ❌ 在飞书群、Slack、公开聊天工具里粘贴完整 token。
- ❌ 把 `~/.config/mify/credentials` 放进任何 git 仓库。
- ❌ 共享机器上把 token 写到 `/etc/` 之类全局位置。

泄露了就立刻去 Mify 控制台吊销重发。
