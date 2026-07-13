<title>【教程】Skills 同步脚本使用指南</title>

<callout emoji="💡">
如果你已经在使用多个IDE工具，可能经常会遇到skills不方便同步的问题
这是一个帮助你进行skills管理的教程：做桌面的skills备份以及IDE的skills同步
</callout>

# Skills 同步背景

## 做这件事的目的

- 让同一个 Skill 同时出现在 `Codex`、`Cursor`、`Kiro`等IDE里
- 在桌面保留一份看得见的 `skills` 备份，方便找回和打包给别人
- 改一次后，一键同步到多个工具，不用手动复制来复制去

## 你会得到什么

- 一个桌面备份目录：`~/Desktop/skills`
- 一个同步脚本：`～/sync-skill.sh`
- 一套推荐工作方式：先在一个主目录修改，再统一同步到其他 IDE

## 你需要准备什么

- 一台已经安装好 `Codex`、`Cursor` 或 `Kiro` 等IDE的电脑
- 桌面新建一个名为「skills」的文件夹

<callout emoji="✅">
如果你现在只想先跑通一次，最推荐把桌面 `~/Desktop/skills` 当成主目录。
这样最直观，也最适合备份。
</callout>

## 先用一句话理解这套方案

你可以把它理解成：

- `桌面 skills`：总备份目录，方便你看见和整理
- `～/（Codex/Cursor/Kiro）/skills`：真正给 IDE 读取 Skill 的目录
- `sync-skill.sh`：搬运工，负责把同一个 Skill 同步到多个地方

# Skill 同步脚本教程（4 步版）

这份教程只讲三件事：**怎么下载、放哪里、怎么启用**。

## 1) 下载脚本

把 `sync-skill.sh` 下载到本地（推荐统一放在一个固定目录）。

<figure view-type="Card"><source mime="application/zip" token="XV0VbzZRRolBXBxmgH6csVHRnee"/></figure>

## 2) 放到固定位置

建议目录：`~/skill-sync-kit/sync-skill.sh`

```Bash
mkdir -p ~/skill-sync-kit
cp /path/to/sync-skill.sh ~/skill-sync-kit/sync-skill.sh
```

## 3) 安装（授予执行权限）

```Bash
chmod +x ~/skill-sync-kit/sync-skill.sh
```

## 4) 启用自动同步

默认（单来源监听，监听 desktop）：

```Bash
~/skill-sync-kit/sync-skill.sh --watch
```

指定单来源监听（例如监听 cursor）：

```Bash
~/skill-sync-kit/sync-skill.sh --watch --from cursor
```

多来源监听（desktop/codex/cursor/kiro 任一改动都会触发同步）：

```Bash
~/skill-sync-kit/sync-skill.sh --watch-all
```

---

**如果对你有帮助，请点个赞吧～**