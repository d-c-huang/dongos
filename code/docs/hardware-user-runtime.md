# USER RUNTIME R1

此版本连续执行正常启动。保留正常 AP idle、BKL、原时限、调度、EOI、用户返回和全部服务；成功路径没有 checkpoint stop，不需要等待照片才能继续。真机 FIRST USER R1 已完成首次 CPL3 入口与 F4 中断捕获，但没有执行首个系统调用，不能作为完整桌面通过的证据。

修复的可观测性问题：原正常启动绘制 S19 后只更新内存标记，随后清除 boot_progress_view；原 trusted user_smp_fail 仅记录 Header/metrics 后停机。因而后续失败会残留旧的 S19 画面。该版本不把旧 S19 当作具体故障位置，也不随意修改锁或超时。

严格私有构建只增加失败显示：user_boot_retire 在原 HW_BOOT_DISABLE 前保存已验证的永久 display view，退役时机不变。原可信 BSP user_smp_fail 完成原 Header/metrics 写入后，保存实际 raw CR3，在已映射的 user_entry 中切回内核根，重置可信内核栈并恢复 kernel xstate，再捕获固定 BSS 报告并经原 screen_draw 的几何检查和缓存 Gate 显示。AP 与不可信 GS 失败仍保留原行为。成功运行不调用报告生产者、不绘制失败页、不主动停车。

报告为 32u64/256B，EMPTY 全零，once 捕获、done 最后发布；只读取永久拥有的数据。CPU、mode、slot、token、selected-return、Header/metrics、raw CR3 和调用数是 BSP 现场。failure_cpu 选择最低逻辑 CPU 编号的 published=1 桥失败，failure_mask 保留所有已发布 CPU；不是按时间排序的全系统首错。若没有已发布桥失败，显示 BSP Header.last_error、最近的事件及进度。LAST EVENT 不是当前致命异常的硬件向量。frame_kind=2 的 USER RIP/OPERATION 等来自永久 selected-return，不能冒充实际异常 Frame 或当前 RIP；无有效选择时为零。

失败重绘只在 BSP、IF=0、内核根和内核 xstate 下进行。直接物理 framebuffer 写者为 BSP compositor；普通 AP 应用仅提交共享窗口数据，不能直接映射该 framebuffer。仍使用原 Gate，关闭/争用时不强行开启。保存的启动 view 只在不返回的失败绘制期间临时使用；保留原 failed/error 字段。

验证应包含实际报告的原生正例与错误实现、debug/release/O0-O2/ELF-COFF、真实共享布局、只读输入/canary/once；精确审查私有 patch 只能延伸原可信失败边界，且不增加成功停机。补充唯一 INIT 首 F4 到再次 commit 的真实 Domain/Bridge 原生序列。Root 对最新全量来源重新构建后执行连续 8 CPU、真实 USB HID/桌面/终端/文件系统读写同步、内盘哨兵及全部代码/ABI 验证；旧清单因新增未导入模块而过期时必须重新构建，不能修改历史清单或放宽来源检查。

真机测试时保持直接连接有线 USB 键鼠，从单只测试 U 盘启动。若进入桌面，移动鼠标、打开终端并输入 help；若显示 DONGOS RUNTIME FAILED，拍完整页面。该失败页是实际失败后显示；正常成功不会停在诊断页。完整真机桌面通过仍需真实结果，不由 VM 或报告推断。
