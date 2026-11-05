# P9IPCEXEC1 实时端点 IPC 客体回归

使用现有 Shell、Catalog、普通 `echo` 配置和生产 `ipc-peer`。两份冻结 runtime7 构建均包含 373 个构建输入。与完整原始树核对后，唯一修改的构建输入是隔离副本中的 `services/apps/echo.dg`。两份 peer ELF 全文件哈希因非 LOAD 部分不同，两段实际 LOAD 内容及权限、虚拟范围相同。生产源码和启动配置未改动。

实际四核 QEMU TCG 正常组以种子 324508639 执行。活端点上的无效句柄、CALL 句柄冒用 WAIT 权限、坏响应地址、坏请求地址均得到规定错误且响应哨兵不变。32 次 CALL 各回传完整八字消息。接着发送生产 peer 的 UD2 触发值，阻塞调用获得 `PeerGone`，响应哨兵仍在。Catalog 事件 14 确认 peer token 268、generation 1 以异常向量 6 结束；事件 15 确认 caller token 269、generation 1 退出 0。Shell WAIT 与 Catalog 一致，外部 UART 完整保留三条阶段标记。

实际错回复组只改夹具的一处期望，使正确回复也会触发不匹配。拒绝探针先通过；随后 caller 退出 `0x09510003`，无回传成功和取消成功标记。peer 保持原 token/generation 和 READY 状态。两组均重读归档 UART 核对标记，临时数据盘 SHA 前后相同，各自 QEMU 都干净退出 0。

宿主 `tests.test_p9_ipc_live_qemu` 与 `tests.test_service_ipc_cancellation` 共 5 项实测通过，零跳过。宿主测试覆盖两模式编译、源差集、UART 交错/重复/缺失及 Shell/Catalog 身份和终态绑定。原生取消测试证据位于 `code/build/test/service-ipc-cancellation/run-b18c37263ec4`。

- [正常组结果](../../../../code/build/test/p9-ipc-live/run-ed8f3b16a1a8/normal/build/guest/result.json) · [UART](../../../../code/build/test/p9-ipc-live/run-ed8f3b16a1a8/normal/build/guest/boot/serial.log)
- [错回复组结果](../../../../code/build/test/p9-ipc-live/run-ed8f3b16a1a8/wrong-reply/build/guest/result.json) · [UART](../../../../code/build/test/p9-ipc-live/run-ed8f3b16a1a8/wrong-reply/build/guest/boot/serial.log)

本次覆盖实时端点 CALL 的确定性子集及故障取消。完整 IPC 语料、泄漏监控、24 小时运行及硬件安全功能仍有各自的验收项。


## AI交付 2026-11-05T13:37:33+00:00 · codex-mcp-50488d53a0084e80

两份冻结构建仅echo隔离替换。真实四核TCG正常组通过4类拒绝和响应哨兵、32次完整8字回传，生产peer收到999触发#UD，caller真实PeerGone/哨兵不变，WAIT与Catalog确认caller退出0/peer异常6；实际错回复负控caller退出0x09510003且peer保持READY。外部UART完整、临时盘SHA不变、两guest退出0。两模块宿主5项零skip，范围仅实时CALL子集和故障取消。
