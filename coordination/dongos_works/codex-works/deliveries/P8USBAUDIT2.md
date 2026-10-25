# P8USBAUDIT2：USB 文件系统启动预算

执行范围：root 修改并冻结 `kernel/user/processes.dg`；本测试执行者仅新增启动预算原生探针／测试，并给四份既有测试补真实共享 `hardware_profile.dg` 来源指纹。四份既有测试的 oracle、原负控、编译与执行路径均未改变；`test_service_launch.py` 的既有 large_request 夹具在领取前已经存在，本轮未改。

生产契约为共享可信 USB_ONLY profile 的 cfg1 文件系统独享 `hz*60` 有界启动预算；全部默认配置和 USB profile 的其它17配置仍为 `hz*10`。零频率、ready 状态不合法、乘法上界越界必须在任何 Catalog 写入前拒绝，BootInfo／Catalog ABI、完整 FAT 审计及其它 guest 期限不受此任务扩大。

新增 `tests/test_usb_startup_budget.py` 直接使用现有完整 `process_catalog_probe.dg` 包装和真实 `user.processes` 模块。每个构建只快照真实生产 catalog、process_abi 和 hardware_profile；USB profile 仅在实际共享 profile 副本改变 USB_ONLY 常量，不提供假模块。debug／release 中各构建默认、USB 正常和 USB 60→10 实际坏源码，共6个构建；全部实际汇编 ELF64／COFF，并原生执行完整 `initialize`。

独立 C oracle 固定 Config=128、Snapshot/Event=64、Catalog=10776 字节及关键偏移，逐字比较完整 Catalog：18配置的依赖／名称／权限／重启计数／独享预算，32配置容量和状态尾部，16物理slot的 NONE／零incarnation，以及64个空事件。hz=0、MAX/scale+1、MAX、已ready输入严格返回原Invalid，整个Catalog和前后守卫保持。USB MAX/60、默认 MAX/10合法边界通过；默认 MAX/60+1 仍合法，USB MAX/10 则拒绝。错误 USB 60→10 源码在两模式均正常返回1被独立 oracle 拒绝，不以crash或超时代替。

本执行者已运行：

```text
python -m unittest tests.test_usb_startup_budget -v
Ran 1 test in 5.702s / OK / 0 skip
```

证据：`code/build/test/usb-startup-budget/run-81c70edf49cb/validation-summary.json`。源码前后SHA一致；默认每模式911条C检查、USB每模式553条，四正常程序返回0、两坏体返回1。

尚未由本执行者运行：五模块正式协调器独立复验、旧四模块重复预检、R6实际客体或物理U盘操作。正式作业及真实同盘USB启动由root执行并在协调器审查note记录。R3／R4／R5原始失败保留，不以宿主预算测试宣称真机或完整USB验收。


## AI交付 2026-10-25T11:22:21+00:00 · codex-mcp-14619bbd432c41a6

生产catalog与6测试/fixture、交付均在主目录冻结：仅USB bool时cfg1=hz*60、早期hz>MAX/60拒绝；default及其它17cfg保持10秒，未改重试/依赖/权限/ABI。新完整catalog native 1test5.702s/0skip，6真实编译ELF/COFF与独立C10776B全对象比较，合法MAX边界、零/溢出/已READY失败不写输出，60->10坏体两模式正常rc1。旧4模块仅names末尾新增真实hardware_profile指纹，不改oracles、索引或控件；没有重复预检，将由协调器正式全5模块独立复验。R6已全编译并由root实际VM验证，结果由main另记，未写H。
