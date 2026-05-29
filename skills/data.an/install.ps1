$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 检测当前环境
$ClaudeSkillDir = "$env:USERPROFILE\.claude\skills"
$TraeSkillDir = "$env:USERPROFILE\.trae-cn\skills"

Write-Host "=== data.an 技能安装 ===" -ForegroundColor Cyan
Write-Host ""

# 步骤 1: 检查并安装 feishu CLI
Write-Host "[1/3] 安装 feishu 技能..." -ForegroundColor Yellow
$feishuCmd = Get-Command feishu -ErrorAction SilentlyContinue
if ($feishuCmd) {
    Write-Host "  feishu CLI 已安装，执行更新..."
    try { feishu update } catch {
        npm install -g @mi/feishu@latest --registry https://pkgs.d.xiaomi.net/artifactory/api/npm/mi-npm/
    }
} else {
    Write-Host "  安装 feishu CLI..."
    npm install -g @mi/feishu@latest --registry https://pkgs.d.xiaomi.net/artifactory/api/npm/mi-npm/
}

# 验证 feishu 技能文件已同步
foreach ($Dir in @($ClaudeSkillDir, $TraeSkillDir)) {
    if ((Test-Path $Dir) -and -not (Test-Path "$Dir\feishu\SKILL.md")) {
        Write-Host "  警告: $Dir\feishu\ 缺少技能文件，尝试同步..." -ForegroundColor DarkYellow
        try { feishu update } catch {
            Write-Host "  请手动运行 feishu update 完成同步" -ForegroundColor Red
        }
    }
}

# 步骤 2: 安装 sql 技能
Write-Host "[2/3] 安装 sql 技能..." -ForegroundColor Yellow

# Claude Code 环境
if (Test-Path $ClaudeSkillDir) {
    New-Item -ItemType Directory -Force -Path "$ClaudeSkillDir\sql" | Out-Null
    Copy-Item -Recurse -Force "$ScriptDir\data-sql\*" "$ClaudeSkillDir\sql\"
    Write-Host "  已复制到 $ClaudeSkillDir\sql\"
}

# Trae CN 环境
if (Test-Path $TraeSkillDir) {
    New-Item -ItemType Directory -Force -Path "$TraeSkillDir\sql" | Out-Null
    Copy-Item -Recurse -Force "$ScriptDir\data-sql\*" "$TraeSkillDir\sql\"
    Write-Host "  已复制到 $TraeSkillDir\sql\"
}

# 步骤 3: 安装 data.an 技能
Write-Host "[3/3] 安装 data.an 技能..." -ForegroundColor Yellow

foreach ($Dir in @($ClaudeSkillDir, $TraeSkillDir)) {
    if (Test-Path $Dir) {
        $CurrentParent = Split-Path -Parent $ScriptDir
        if ($CurrentParent -eq $Dir) {
            Write-Host "  data.an 已在 $Dir 下，跳过复制" -ForegroundColor Yellow
        } else {
            New-Item -ItemType Directory -Force -Path "$Dir\data.an" | Out-Null
            # 复制所有文件和子目录（含 data-sql/、install 脚本等）
            Copy-Item -Recurse -Force "$ScriptDir\*" "$Dir\data.an\" -Exclude "__pycache__","*.pyc"
            Write-Host "  已复制到 $Dir\data.an\"
        }
    }
}

Write-Host ""
Write-Host "=== 安装完成 ===" -ForegroundColor Cyan
Write-Host ""

# 输出检查结果
$envs = @(
    @{ Name = "Claude Code"; Dir = $ClaudeSkillDir; SqlDir = "sql" },
    @{ Name = "Trae CN";     Dir = $TraeSkillDir;   SqlDir = "sql" }
)

foreach ($env in $envs) {
    if (Test-Path $env.Dir) {
        Write-Host "[$($env.Name)] $($env.Dir)"
        if (Test-Path "$($env.Dir)\feishu\SKILL.md") { Write-Host "  feishu  OK" -ForegroundColor Green } else { Write-Host "  feishu  MISSING (请运行 feishu update)" -ForegroundColor Red }
        if (Test-Path "$($env.Dir)\$($env.SqlDir)\SKILL.md") { Write-Host "  sql     OK" -ForegroundColor Green } else { Write-Host "  sql     MISSING" -ForegroundColor Red }
        if (Test-Path "$($env.Dir)\data.an\SKILL.md") { Write-Host "  data.an OK" -ForegroundColor Green } else { Write-Host "  data.an MISSING" -ForegroundColor Red }
        Write-Host ""
    }
}

Write-Host "提示: 首次使用时会自动引导你完成飞书登录和数据工厂 Token 配置，无需手动操作"
