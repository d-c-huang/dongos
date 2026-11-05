# P9IPCEXEC1 — [P9] 真实 CPL3 实时端点 IPC 与故障取消回归

负责人：codex。状态：待领取。

用隔离 runtime7 fixture 仅替换普通 echo app 源，保留生产内核、syscall、IPC peer、权限装配和启动清单。对真实活端点运行确定性 CALL 多字消息往返、无效句柄/坏地址与输出原子性，再触发原 ipc-peer UD2，验证 caller 获得 PeerGone、peer 终态向量6，保留进程和独立外部UART证据。从冻结构建运行临时虚盘上的实际 QEMU，由协调者执行；宿主检查不启动虚拟机。保持正常/失败构建和源变更界限，实际 guest 负控验证错回复或错结果被拒绝。范围是实时端点子集，不代表全IPC模糊或24小时门禁。

## 可修改文件

- `tests/p9_ipc_live_fixture.dg`
- `tests/run_p9_ipc_live_qemu.py`
- `tests/test_p9_ipc_live_qemu.py`
- `codex-works/deliveries/P9IPCEXEC1.md`

## 定向验收

- `module:tests.test_p9_ipc_live_qemu`
- `module:tests.test_service_ipc_cancellation`

交付：`codex-works/deliveries/P9IPCEXEC1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。
