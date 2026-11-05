# P2PCIDWHPX1 — [P2] 当前 Windows WHPX 的严格逐 CPU PCID 复验

负责人：codex。状态：待领取。

现有归档构建的原路径已漂移，重建当前P2 PCID专用隔离镜像，协调者用现有runner WHPX显式userspace interrupt controller路径和--require-pcid执行，不修改宿主设置，不放宽PCID、AP及原始证据门。只用临时虚盘。宿主checks不启动虚拟机。若实际后端启动或PCID能力失败，留原始状态和日志，不用TCG替代、不验收阶段。

## 可修改文件

- `codex-works/deliveries/P2PCIDWHPX1.md`

## 定向验收

- `module:tests.test_p2_pcid`
- `module:tests.test_p2_pcid_build`

交付：`codex-works/deliveries/P2PCIDWHPX1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。
