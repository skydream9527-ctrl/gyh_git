#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 检测当前环境
CLAUDE_SKILL_DIR="${HOME}/.claude/skills"
TRAE_SKILL_DIR="${HOME}/.trae-cn/skills"

echo "=== data.an 技能安装 ==="
echo ""

# 步骤 1: 检查并安装 feishu CLI
echo "[1/3] 安装 feishu 技能..."
if command -v feishu &>/dev/null; then
    echo "  feishu CLI 已安装，执行更新..."
    feishu update || npm install -g @mi/feishu@latest --registry https://pkgs.d.xiaomi.net/artifactory/api/npm/mi-npm/
else
    echo "  安装 feishu CLI..."
    npm install -g @mi/feishu@latest --registry https://pkgs.d.xiaomi.net/artifactory/api/npm/mi-npm/
fi

# 验证 feishu 技能文件已同步（两个环境都检查）
for DIR in "${CLAUDE_SKILL_DIR}" "${TRAE_SKILL_DIR}"; do
    if [ -d "${DIR}" ] && [ ! -f "${DIR}/feishu/SKILL.md" ]; then
        echo "  警告: ${DIR}/feishu/ 缺少技能文件，尝试同步..."
        feishu update || echo "  请手动运行 feishu update 完成同步"
    fi
done

# 步骤 2: 安装 data-sql / sql 技能
echo "[2/3] 安装 sql 技能..."

# Claude Code 环境
if [ -d "${CLAUDE_SKILL_DIR}" ]; then
    mkdir -p "${CLAUDE_SKILL_DIR}/sql"
    cp -r "${SCRIPT_DIR}/data-sql/"* "${CLAUDE_SKILL_DIR}/sql/"
    echo "  已复制到 ${CLAUDE_SKILL_DIR}/sql/"
fi

# Trae CN 环境
if [ -d "${TRAE_SKILL_DIR}" ]; then
    mkdir -p "${TRAE_SKILL_DIR}/sql"
    cp -r "${SCRIPT_DIR}/data-sql/"* "${TRAE_SKILL_DIR}/sql/"
    echo "  已复制到 ${TRAE_SKILL_DIR}/sql/"
fi

# 步骤 3: 安装 data.an 技能
echo "[3/3] 安装 data.an 技能..."

for DIR in "${CLAUDE_SKILL_DIR}" "${TRAE_SKILL_DIR}"; do
    if [ -d "${DIR}" ]; then
        CURRENT_PARENT="$(dirname "${SCRIPT_DIR}")"
        if [ "${CURRENT_PARENT}" = "${DIR}" ]; then
            echo "  data.an 已在 ${DIR} 下，跳过复制"
        else
            cp -r "${SCRIPT_DIR}" "${DIR}/data.an"
            echo "  已复制到 ${DIR}/data.an/"
        fi
    fi
done

echo ""
echo "=== 安装完成 ==="
echo ""

# 输出检查结果
for DIR in "${CLAUDE_SKILL_DIR}" "${TRAE_SKILL_DIR}"; do
    if [ -d "${DIR}" ]; then
        ENV_NAME="Claude Code"
        SQL_DIR="sql"
        [[ "${DIR}" == *".trae-cn"* ]] && ENV_NAME="Trae CN"

        echo "[${ENV_NAME}] ${DIR}"
        [ -f "${DIR}/feishu/SKILL.md" ] && echo "  feishu  ✓" || echo "  feishu  ✗ (请运行 feishu update)"
        [ -f "${DIR}/${SQL_DIR}/SKILL.md" ] && echo "  sql     ✓" || echo "  sql     ✗"
        [ -f "${DIR}/data.an/SKILL.md" ] && echo "  data.an ✓" || echo "  data.an ✗"
        echo ""
    fi
done

echo "提示: sql 技能需要配置环境变量 DATAWORKS_TOKEN_ID，请参考 data-sql/scripts/.env"
