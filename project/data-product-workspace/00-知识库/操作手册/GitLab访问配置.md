# 小米GitLab访问配置

## 基本信息
- GitLab地址：https://git.n.xiaomi.com
- 用户名：gongyunhe
- 邮箱：gongyunhe@xiaomi.com
- 访问Token：`SXS14HZ_Und2nvQvmA8udG86MQp1OjE2bXEK.01.100xzfh0z`
- Token权限：读取你的个人仓库

## 个人仓库
- 主项目：ICE Data Workbench v3（AI数据工作流工作台）
- 仓库地址：https://git.n.xiaomi.com/gongyunhe/gyh_gitlab
- 技术栈：FastAPI后端 + React 19前端 + 多Agent协作系统

## Clone方式
```bash
# 使用token克隆（避免每次输入密码）
git clone https://oauth2:SXS14HZ_Und2nvQvmA8udG86MQp1OjE2bXEK.01.100xzfh0z@git.n.xiaomi.com/gongyunhe/gyh_gitlab.git
```

## 全局Git配置建议
```bash
git config --global user.name "gongyunhe"
git config --global user.email "gongyunhe@xiaomi.com"
```

## Token安全说明
- Token仅保存在本地配置中，不要提交到公开仓库
- 如需轮换token，在GitLab个人设置 → Access Tokens中生成新的
