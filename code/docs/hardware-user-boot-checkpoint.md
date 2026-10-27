# S19 后的 AP 发布前检查点

正常版本的 S19 是最后一次可见重绘；S20至S23只更新内存。真机仍显示S19、8CPU、error0，不能据此认定锁死，也不能证明USB服务已经执行。

本版显式入口为 `DongOS USER CHECK R1`，主动停止画面为 `DONGOS USER CHECKPOINT`。它保持正常用户SMP选择器为1，真实执行原 `ud.acquire` 和 `services.enable_smp`，只在后者成功返回后、`user_boot_publish` 之前插入唯一停止调用。没有修改锁、原2秒期限、AP就绪判断、用户态策略或设备权限。新AP用户态入口尚未发布，因此此处重绘不会占用AP等待新域锁的限时窗口；停止后不恢复正常流程。

检查点纯观察模块从真实boot Report和Domain捕获17个u64/136字节的固定报告，发布done最后写入。仅由原screen_draw、几何检查和cache Gate显示15行，末行底部470像素，不增加第二个帧缓冲写者。

正常目标值为：CHECKPOINT=15（十六进制21边界）、CPU COUNT=8、CHECK ERROR=0、BOOT READY=1、BOOT FAILED=0、AP PUBLISHED=0、DOMAIN READY=1、DOMAIN FAILED=0、LOCK=1、OWNER=0、ONLINE MASK=FF、BARRIER=0、EXPECTED=0、COMPLETED=0、ENABLE OK=1。CHECKPOINT是本诊断选定的边界编号，不是正常boot_progress_phase的原值。ENABLE OK只表示内核 `enable_smp` 已返回，不表示USB服务、桌面或键鼠成功。

若仍是S19，此新增边界尚未显示，需要继续查锁前后或重绘返回；若显示检查点且上述字段正确，说明锁获取和内核服务初始化已越过，下一步才定位AP交接与CPL3运行。原有早期失败仍走原HW_BOOT_ERROR，不构造USB首错；本版没有执行任何用户服务，USB驱动错误信息仍待后续诊断。

构建只修改私有kernel-profile-src中的root导入、user_boot唯一停止点及新观察模块，以及私有entry的标量显示和停止例程。services_run保持原字节并用SMP=1重新汇编，17份服务ELF和SERVICES.BIN逐字保留。原始正常构建日志保留原SHA；其中相对路径按真实构建cwd解析为同一现存文件，严格检查执行程序、参数顺序、定义、链接对象及两个EFI manifest消费者。另有独立诊断manifest，绝不冒充正常桌面成品。

原生测试执行真实捕获模块，覆盖3至16CPU、未发布/锁/错误/域状态/空指针、输入不变和once，debug/release、O0/O2、ELF/COFF，三种真实坏体必须被C断言捕获；私有patch必须唯一位于enable成功之后和AP发布之前。根协调器用真实8CPU单USB及三可写内盘哨兵核验报告、实时Domain、SMP_ENABLED、未发布AP入口、无用户服务/设备权限、原执行代码和完整15行像素。验证结果以任务复验/审查记录为准。

请从U盘启动后拍完整画面到最底部ENABLE OK。主动停在此页是预期，不进入桌面，F12不响应。USB写入只替换经备份的四个文件，保留原SanDisk分区和身份，并做flush、回读及FAT32 rb检查。
