<title>【教程】给产品小白的最短教程：Git使用</title>

<callout emoji="😆">
看到Git别害怕，文档的内容**只需要复制粘贴即可**啦。你要做的唯一一件事就是下载IDE工具。
极力推荐产品小白同学下载OpenAI出品的  [codex](https://chatgpt.com/zh-Hans-CN/codex/get-started/)（点击下载）开始IDE之旅～
</callout>

# 做这件事的目的

这件事不是为了学 Git，而是为了让你的文件能被**其他产品同学、研发、设计**一起复用，解决 4 件事：

- 所有项目资产（如MD、HTML、CSS、图片、组件）可作为共享上下文
- Git仓库的内容作为协同文件，有较好的组件化架构，可生成一致性更好的项目逻辑和原型页面
- 预览内网可见的可交互HTML原型
- 给研发真实可查看、可复用的源文件参考

---

# Git 里应该放什么

- **规范内容：**统一存放 README、Design System、handoff 规范等项目级约束。
- **原型共用内容：**统一存放样式版本、全局 CSS、组件库、飞书文档映射表等共享资产。
- **开发对齐内容：**统一存放组件表、字段表、页面命名表等需要产研持续共读的事实。

例如⬇️

```Plain Text
产品仓库/
├── index.html                         ← 产品原型目录入口（桌面端，只做卡片导航）
├── mobile.html                        ← 主壳入口（移动端，唯一 App Shell）
├── serve-https.py                     ← 本地 HTTPS 开发服务器（手机真机预览）
│
├── _shared/                           ← 全局共享层
│   ├── product-ai/                    ← 产品工作方式、AI 约束、设计规范
│   ├── lookups/                       ← 组件 / 字段 / 页面 / 飞书文档速查表
│   ├── dev-bridge/                    ← 产品 ↔ 研发桥接协议与注册表
│   ├── exports/
│   │   ├── mobile-shell/              ← `mobile.html` 当前 live runtime
│   │   └── ai-render-components/      ← AI 渲染类共享组件
│   ├── versions/
│   │   └── v1.0.0/                    ← 冻结快照（版本页只读这里）
│   └── route-registry.json            ← 目录卡片唯一数据源
│
├── Vx.x功能名/                        ← 版本孵化目录
│   ├── 【SPEC】...md                  ← 原型设计规范
│   ├── 【PRD】...md                   ← 需求文档（如有）
│   ├── styles.css                     ← 版本私有样式
│   ├── page.js                        ← 版本私有交互逻辑
│   ├── handoff.json                   ← 产品 → 研发交接文件
│   └── mock-data/                     ← Mock演示数据（如有）
│
├── V1.0登陆与对话/                     ← 此处仅为版本示例
├── V1.1对话卡片/
├── V1.2任务页/
├── V1.3移动端增强与信任/
├── V2.0拍题与批改/
├── V2.1：任务视图/
├── V3.0AI白板讲解/
│
├── scripts/                           ← 脚手架、检查、构建脚本
└── assets/                            ← 静态资源（字体、图片等）
```

也可以把仓库理解成 4 层：

- **版本层**：`Vx.x功能名/`，承接单个版本的 Spec / PRD / 原型 / `page.js` / `styles.css` / `handoff.json`
- **shared 层**：`_shared/exports/` + `_shared/versions/`，分别负责主壳 live runtime 和冻结快照
- **lookup 层**：`_shared/lookups/`，统一页面、字段、组件、飞书文档索引
- **bridge 层**：`_shared/dev-bridge/`，把产品表达映射到研发实现，减少“看懂 Demo 但接不住”的问题

# 飞书和 Git 怎么配合

你可以把它理解成：

- **飞书**：给人看，适用讨论，可引用git资源
- **Git**：给AI看，适用开发

所以我们可以做一个**飞书链接和git文档的映射**，让AI每次生成需求md文档时同步到飞书链接

这样分工最清楚：

- 飞书文件用于评审
- Git 文件用于实际开发
- 通过GitLab pages预览链接快速看页面效果

> **重要：Git 不是预览工具。**Git 负责存文件；预览链接来自后续的内网发布或静态预览服务。

---

# 第一次使用：如何申请 Git 并在电脑上部署

### 第一步：申请仓库权限

找项目负责人，开通目标仓库权限。

### 第二步：申请并配置 SSH Key

你可以把下面这段**整段复制给 IDE**，让它一步步带你做：

> 绿色内容请替换

```Bash
我是代码小白，请你帮我完成 SSH Key 配置，用于 git.n.xiaomi.com。
请严格按下面步骤执行，并每一步都告诉我结果：

1）先检查是否已有 SSH 公钥文件：
- ~/.ssh/id_ed25519.pub
如果存在，就直接打印该公钥，不要覆盖。

2）如果不存在，再生成：
ssh-keygen -t ed25519 -C "我的公司邮箱"
默认路径，按回车；如提示文件已存在，不要覆盖，先问我。

3）生成后打印公钥，方便我复制：
cat ~/.ssh/id_ed25519.pub

4）提醒我去网页操作，等待我粘贴保存完成后再继续。

5）最后帮我验证：
ssh -T git.n.xiaomi.com
告诉我是否成功。
```

帮你生成好SSH公钥后，请打开自己的[SSHkey配置页面](https://git.n.xiaomi.com/-/user_settings/ssh_keys)⬇️

<grid>
<column width-ratio="0.333333">
![图片展示的是GitLab的SSH Keys配置页面。左侧导航栏选中“SSH Keys”。页面上方有“User Settings / SSH Keys”标题，下方说明SSH密钥用于在计算机和GitLab之间建立安全连接。列表显示了已添加的SSH密钥信息，包括标题、Key、使用类型、创建时间、最后使用时间及有效期等。右上角有“Add new key”按钮，用红色框突出显示，提示用户点击添加新SSH密钥。该图片与文档中“申请并配置SSH Key”步骤相关，指导用户在GitLab中配置SSH密钥。](https://feishu.cn/file/TfVDbNmbxoC9q2xg696czNKZnuc)
</column>
<column width-ratio="0.333333">
![图片展示的是GitLab中SSH Keys配置页面。左侧为用户设置菜单，选中“SSH Keys”。右侧是添加SSH密钥的界面，提示可为密钥添加标题，密钥类型默认为“Authentication & Signing”，可设置过期日期。下方有“Add 自动生成密钥”按钮，下方“Key”区域用于粘贴生成好的SSH密钥。该图片与文档中“申请并配置SSH Key”步骤相关，用于指导用户在GitLab上配置SSH密钥，完成SSH Key的申请与配置。](https://feishu.cn/file/AaH1b2n60odiQSxHebzcE95Onye)
</column>
<column width-ratio="0.333333">
![图片展示的是GitLab中SSH Keys配置页面。页面左侧为导航栏，选中“SSH Keys”。右侧显示“Add an SSH key”提示，下方有“Add key”按钮，用于添加SSH密钥。页面还显示了SSH密钥的格式示例，以及“Usage type”和“Expiration date”等设置区域，其中“Usage type”处有红色框标注，提示“这里会自动填写你的邮箱”。该图片与文档中“申请并配置SSH Key”步骤相关，用于指导用户在GitLab中添加SSH密钥。](https://feishu.cn/file/QY4YbVI2UopmzixX6rJceu1enrp)
</column>
</grid>

### 第三步：安装 Git，下载仓库

如果电脑里还没有 Git，请先安装。跟你的IDE说，例如：

```Bash
请你帮我安装Git，我的仓库链接是 "复制你的仓库地址"，请你拼接成 SSH clone 地址并下载仓库到本地。
然后操作以下内容，每一步都先告诉我结果再继续：
1. 先切到主分支 `main`，拉取最新内容
2. 基于最新的 `main` 创建一个新分支，分支名叫 `feat/绿色内容替换成你的需求名`
3. 确认我现在不在 `main`，而是在新分支上
4. 后续我的修改都提交到这个新分支，不要直接提交到 `main`
5. git config --local user.email  "您的邮箱@xiaomi.com"  --公司gitlab规范要求
5. 最后告诉我这个仓库在我本地的地址，后续我应该在哪里操作
```

### 第四步：打开仓库，开始施工

把这个文件夹拖拽到你的IDE面板中（或者直接跟IDE口述你要修改的文件）即可。跟你的IDE说，例如：

> 绿色内容请替换仓库在你本地的地址，如我的本地仓库地址是ai_tutor_prds

```Bash
帮我在ai_tutor_prds新建一个V2.2的文件夹，使用我的skill工具帮我生成prd的md文件，我的要求是……
帮我修改ai_tutor_prds/V1.1中的prd的md文档，我的要求是……
```

### 第五步：施工完成，上传分支

1. **或者直接跟IDE口述你要修改的文件即可**

跟你的IDE说，例如：

> 绿色内容请替换

```Bash
我改好了，你总结一下改动帮我提交到远端吧，然后把MR链接发给我。  --不要直接合并Main哦～
MR名称可写成：绿色内容替换成你这次改动的一句话说明。         
```

成功判定：

IDE 告诉你分支已经推送成功，并给你一个可以发起合并请求（Merge Request）的分支结果，可以**让IDE直接把MR链接给你**。

![图片图片展示的是在GitLab页面上操作的界面。界面中显示了Kiro的提交信息，内容为提交到feat/lxj分支，删除了569个文件，新增了serve - https . py 。 以及远程给出的merge request链接，提示需合并到main时可去那里创建MR。下方有Credits used、Elapsed timeme等信息，还显示了Checkpoint和Restore选项，以及“链接给我”按钮。该图片与文档中“得劲儿魔法：放弃以上五步”内容相关，展示了在GitLab上操作后的提交结果及链接信息。](https://feishu.cn/file/LDw5bQ5bDo2uUexmZDLcZAfenze)

1. **接下来的操作要在GitLab 页面上操作**

- 填写本次改动说明：改了什么、影响哪个文件夹、预览链接是什么
- 指定至少 1 位 reviewer
- 催促 reviewer 检查，通过后让他合入`main`

### 得劲儿魔法：放弃以上五步

完成以上后，你关于git的操作可以都建立在同一个IDE对话中，上下文会帮你解决很多问题，比如跟你的IDE说：

> 绿色内容请替换

```Bash
我的V1.1文档内容更新好了，帮我上传远端，备注“V1.1的原型图设计规范更新”，MR发我。
我要开始今天的工作了，请你帮我拉下远端最新代码覆盖本地
```

<callout emoji="🤾‍♂️">
所以，在开工之前，记得先pull下远端最新的代码哦～
</callout>

---

# 如何给同事预览 Git 里的 HTML

通过**GitLab Pages**，把仓库里的 html/css/js 自动发布成一个网站，给一个内网的可访问链接，在git push之后能自动刷新，你可以把把这个预览链接贴回飞书，以供大家对照prd查看～

所以正确关系是：

`Git 仓库链接 = 源文件入口`

`内网预览链接 = 页面效果入口`

> AI老师原型图地址：[http://ai-tutor-prds-6af886.pages.n.xiaomi.com/](http://ai-tutor-prds-6af886.pages.n.xiaomi.com/)
> 
> ⚠️ 内部项目，受限访问。需有仓库访问权限才可查看哦～

![图片展示了GitLab界面中AI Tutor Prds项目的相关设置。左侧为项目导航栏，显示了Pinned、Issues、Merge requests等选项。右侧上方是搜索栏，下方是.gitlab-ci.yml文件内容，包含GitLab Pages部署配置，如部署后访问链接、pages部署阶段、script脚本等信息，还列出了paths和rules等配置项。该图片与文档中介绍通过GitLab Pages把仓库html/css/js自动发布成网站的内容相关，展示了相关配置文件。](https://feishu.cn/file/PdU8bMMbSoGwNHxtRxNcA70rn9d)

---

# 效果展示

![图片展示了小米AI家长助手APP的登录与引导界面。左侧是登录页面，有“一键登录小米账号”和“获取邀请码登录”两种方式，还提示可使用手机号登录。中间是登录方式选择界面，可选择“密码登录”“手机号登录”“微信登录”“小米账号登录”。右侧是小米账号登录界面，有“使用小米账号登录”“获取邀请码登录”“手机号登录”“微信登录”等选项，下方有“一键登录小米账号”按钮。该图片与文档中介绍小米AI家长助手登录方式的内容相关，直观呈现了登录界面样式。](https://feishu.cn/file/BBN2b9hEFoi7flxotZCcyNRknFc)

![图片展示了AI老师原型图的页面内容。左侧是AI老师原型图的介绍，包括其功能、使用场景等。中间部分有“我有疑问”“我有答案”“我有想法”三个板块，分别对应提问、回答和分享功能，还展示了AI老师与用户互动的示例。右侧是“我有答案”板块的详细内容，包括答案类型、答案示例、答案生成逻辑等。该图片与文档中介绍AI老师原型图的内容相关，直观呈现了其功能和使用情况。](https://feishu.cn/file/P84DbehIeo22McxSIt6ceYxyn1d)

![图片展示了AI老师产品页面的三个步骤。步骤1是账号管理，列出账号信息、账号管理、账号迁移、账号迁移日志、账号迁移提示等功能；步骤2是账号迁移，有账号迁移、账号迁移日志、账号迁移提示等操作；步骤3是个人账号信息确认，有账号信息、账号迁移、账号迁移日志、账号迁移提示等选项。该图片与文档中介绍AI老师产品相关，是对产品页面操作步骤的直观呈现。](https://feishu.cn/file/Matjb0msJoVbkXxIg9tcipginRd)

<grid>
<column width-ratio="0.200000">
![图片展示的是AI老师原型图的手机预览界面。上方显示网址“http://10.192.191.24:3000/mobile.html”。界面标题为“手机预览”，并提示自动读取总览目录，点击进入全屏交互原型。下方分为V1.x和V2.x两个版本，每个版本下有对应功能模块，如V1.0 - V1.2版本下的登录与对话、对话卡片交互、任务Tab页等功能，V2.1 - V2.2版本下的拍照搜题、作业批改等功能。该图与文档中介绍AI老师原型图地址及功能的内容相关，直观呈现了原型图的界面及功能模块。](https://feishu.cn/file/YYIXbFGZToDzcwxdNRlc6MzynVc)
</column>
<column width-ratio="0.200000">
![图片展示了AI老师原型图中页面功能模块的规划。分为3.1登录与引导、3.2主页面构成与账号管理、3.3AI老师主入口三个部分。3.1部分涵盖登录方式选择、手机号与密码登录、首次引导等；3.2部分保留首页、抽屉、账号详情等，作为后续页面对齐标准；3.3部分聚焦AI老师统一入口，涵盖空态承接、多模态输入等。图片与上下文紧密相关，是对AI老师原型图功能规划的详细说明。](https://feishu.cn/file/Om0kbgP1MofnU6xPgwDcVJMUnNb)
</column>
<column width-ratio="0.200000">
![图片展示的是AI老师原型图的登录界面。上方显示网址“http://10.192.191.24:3000/mobile.html?page=V1.0%CE%E7...”，右上角有“退出”按钮。界面主体部分有卡通人物形象，下方文字为“一站式家长伴学 让成长更轻松”，并有“一键用小米账号登录”和“登录其他小米账号”两个按钮。最下方提示已阅读并同意《小米账号用户协议》和《小米账号隐私政策》。该图片与文档中介绍通过GitLab Pages发布仓库html/css/js，生成内网可访问链接的内容相关，展示了内网预览链接的效果。](https://feishu.cn/file/IZJgbYXS7oL0THxfQoscx8R3n1g)
</column>
<column width-ratio="0.200000">
![图片展示的是AI老师界面，背景为浅蓝色。上方显示网址“http://10.192.191.24:3000/mobile.html?page=V1.0%CE7...”，右上角有“退出”按钮。界面中部以大字呈现“AI老师，内容由AI生成”，下方有“嗨，我是你的AI老师”及介绍，可尝试发作业让其安排任务或答疑。下方有三个蓝色按钮，分别为“帮我制定今天的学习计划”“帮我分析孩子最近一周的学习状态”“拍一下这道题，看看孩子哪里没懂”。最下方是输入框，提示“发消息或按住说话...”。](https://feishu.cn/file/HxhvbFy7xoFkqGxPKgdcv9Vunec)
</column>
<column width-ratio="0.200000">
![图片展示的是一个AI家长助手界面。左侧显示“小米家长”身份，下方有“新建对话”按钮。右侧是历史记录，包含“整理班级群里的作业截图”“今晚数学先做哪几题”“这道应用题孩子卡住了”“帮我整理本周英语任务”“语文默写错题怎么复习更高效”等对话内容，每条记录下方有对应的时间。该图片与文档中介绍AI家长助手功能的内容相关，直观呈现了助手的对话界面及历史记录情况。](https://feishu.cn/file/CUKMbJiP7o1dkPxBXYXc2Z3Zndc)
</column>
</grid>

# 致谢

感谢<cite type="user" user-id="ou_fc68e3011a84b8adb3c2f8fba93c4f48" user-name="贺洋洋"></cite><cite type="user" user-id="ou_5e900b83dcf112cffc88facce624f418" user-name="冯海涛"></cite>老师的协助以及其他产品老师的支持，如果在实操中有困难的地方可联系作者更新文档，一起碾压0代码基础同学AI转型的门槛～

**如果对你有帮助，请点个赞吧～**