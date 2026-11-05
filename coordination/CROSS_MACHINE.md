# 跨研发电脑接续

仓库：<https://github.com/d-c-huang/dongos>，分支 `main`。本次检查点为 2026-11-05：296 个任务，含 27 个归档任务；269 个非归档任务为 242 integrated、24 accepted、2 submitted、1 rework。296 份事件文件保留 3,878 条历史事件。后续数量以协调器实时状态为准。

任务书、候选源码、测试、交付、审查、阶段图，以及协调器生成的 `dongos_works/state/tasks/` 和 `state/events/` 均随仓库同步。本批已验收的 P5/P9 主线源码一起提交，避免记录与源码脱节。`accepted` 和 `integrated` 不合并解释；P8BOOTCONSOLE1 仍为 rework rev17，真实硬件/客体门见 [整体任务图](dongos_works/progress-map.md)。

## 新电脑首次启动

需要 Git、Python 3.12+；读取和恢复任务不需要模型服务、编译器或虚拟机。

```powershell
git clone https://github.com/d-c-huang/dongos.git
cd dongos
git switch main
python coordination/coordinate.py --project dongos state-sync
python coordination/coordinate.py --project dongos validate
python coordination/coordinate.py serve
```

浏览器访问 `http://127.0.0.1:8765` 并选择 DongOS。`project.json` 的源码路径是相对路径 `../../code`，可以更换磁盘或目录。空本地数据库会从 state 自动恢复任务状态、rev、依赖、审查说明、历史验收摘要与事件；不要根据任务书标题重建一套 todo。

AI 客户端重新配置本机路径；Codex 使用 coordinator 角色，其它客户端使用 worker。以下命令只输出配置，不启动 AI：

```powershell
python coordination/coordinate.py mcp-config --client codex
python coordination/coordinate.py mcp-config --client cursor
```

## 已有开发副本换机同步

先保存旧电脑改动并提交、推送。新电脑若有正在运行的任务，先按协调器流程完成或停止，保留其记录，再拉取：

```powershell
git pull --ff-only origin main
python coordination/coordinate.py --project dongos state-sync
python coordination/coordinate.py --project dongos validate
```

`--ff-only` 被拒绝时先检查双方提交和任务身份，不强推、不重置或手改任务 rev。state 合并必须保留事件与既有验收，不能以新电脑的旧状态覆盖较新状态。组件声明已集成也不能直接推断整个阶段完成。

## 哪些记录仍留在原电脑

`.local/` 的 SQLite、端口/锁、活动作业、隔离运行副本、原始日志，以及 `code/build/` 的镜像/原始硬件捕获不进 Git；派生 `index.json` 由本机生成，不再跟踪。任务中的历史验证摘要、指纹和审查结论会保留，但绝对日志路径可能只在原电脑存在。复验需要的原始镜像/捕获应另行归档传递，或在新机器重新运行原检查，不能声称这些原始产物已随代码上传。

Git 换行策略可能改变工作文件字节；历史 SHA 仍绑定原测试输入，不应手改成新 SHA 来假装重新验收。领取需要旧 `.local/runs` 候选的任务前，应按原交付恢复候选并重新复验。API 密钥、模型服务配置和本机登录凭据由新机器单独配置。

每次交接应确认 state-sync 无冲突、validate 无问题，并上传任务状态及其对应源码。本次上传前使用 Git 暂存树在独立空目录中实际恢复全部任务和事件，核验结果保存在 [跨机恢复核验](dongos_works/reviews/2026-11-05-cross-machine-sync.json)。

## 已知历史原文缺口

本次从固定 Git 提交按原字节恢复了 8 份归档任务书，来源和 SHA 见 [原文恢复清单](dongos_works/reviews/2026-11-05-task-document-recovery.json)，没有重新领取或复活归档任务。

DeepSeek D1–D4 的独立 `deliveries/D1.md` 至 `D4.md` 未在现有文件或已获取的 Git 历史中找到。其原任务列表、状态与事件、源码及 [2026-10-16 联合审查记录](dongos_works/deepseek-works/reviews/2026-10-16-D1-D4.md) 仍完整保留。本次不伪造缺失的独立交付原文，也不改动四项历史 accepted 状态；恢复核验会单独列出这四个缺口。
