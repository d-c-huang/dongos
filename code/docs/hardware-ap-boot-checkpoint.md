# AP CHECK R1

真机USER CHECK R1已确认：锁由BSP持有、内核enable_smp成功、AP入口尚未发布，所有错误为零。因此此前S19旧画面不能用作锁获取失败证据。本版继续检查真实IPI交接、CPU激活和服务队列投影。

本版保持正常SMP=1、原锁和2秒期限、IPI发送、user_smp_activate及BSP等待ready2/队列投影代码。仅在私有user_boot.asm中，将AP成功activate之后的idle入口替换为记录自己的park位，然后CLI/HLT停驻；BSP在投影成功之后，按原until限时等待所有诊断park位，再捕获并主动停止，尚未retire/unlock。失败分支保留。这是显式诊断行为改变，不代表AP后续idle、BKL争用、调度、CPL3、USB或桌面已通过；不将停车逻辑集成进正常路径。

入口 `DongOS AP CHECK R1`，画面 `DONGOS AP CHECKPOINT`。固定136字节/17个u64报告显示15行，原screen_draw/cache Gate和几何检查保持，末行底部470像素。正常8CPU目标：CHECKPOINT=17（十六进制23边界）、CPU COUNT=8、CHECK ERROR=0、AP PUBLISHED=1、LOCK=1、OWNER=0、ONLINE MASK=FF、READY MASK=FF、ERROR MASK=0、FIRST ERROR=0、FIRST CPU=10（十六进制16，表示无首错CPU）、QUEUE COUNT非零且不超过10（十六进制16）、BOOT FAILED=0、DOMAIN FAILED=0、PARKED MASK=FE。掩码包含逻辑CPU位；READY包含BSP，PARKED只包含AP。

报告只读真实boot Report、Domain、队列Engine和每个完整256字节Header；Header.ready及last_error逐CPU检查，首错保持最低逻辑CPU。捕获once，完成标志最后发布。不执行用户服务，也不构造USB错误码。若检查点通过，后续才定位解锁、AP idle/调度与服务执行；若原错误路径报告失败，应记录全部字段，不能把诊断park等待超时直接解释为正常版本同一故障。

私有构建增加观察模块/root导入和BSP stop hook，替换4个内核对象（entry、dong_probe、services_run和user_boot），共9个真实编译/链接命令。services_run原字节与SMP=1保持，17份服务ELF及SERVICES.BIN逐字保持。严格原始日志/工具/参数/链接对象/overlay/IMG/两EFI消费者校验与独立diagnostic manifest均保留。正常默认源不变。

原生测试执行真实capture，3..16CPU、每CPU未ready/错误/空Header、park掩码、队列范围、输入不变/once和真正错误体，在debug/release与O0/O2执行并汇编ELF/COFF。实际256字节Header声明用于native边界，ready偏移200、last_error208需吻合。root VM另外核对真实8CPU各Header、GS、AP RIP/IF0/HLT停车位置、发布指针与park掩码、队列、无用户服务和硬件权限、原代码及15行像素、整USB和三可写内盘未变。通过独立复验及实际审查后才写原SanDisk H，备份/flush/回读并做native FAT32 rb检查。

启动后请拍整屏到最底部PARKED MASK。该页主动停留，不进入桌面，F12无响应属预期。
