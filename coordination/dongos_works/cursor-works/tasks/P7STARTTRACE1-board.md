# P7STARTTRACE1 — [P6/P7/P8] GUI READY前文件与设置启动超时的只读分阶段捕获

负责人：cursor。状态：待领取。

当前正常runtime7 USB-only四核TCG，FIFO及仅恢复HEAD Bridge的严格同源A/B均cfg15 files、cfg17 settings在10s STARTING期限Timeout05110007，cfg14 terminal/16editorready，缺P7_CLIENTS_READY，未进入HID/长文件/第二启；证据code/build/test/p6-bkl-integration/run-20261106/{usb-guest,usb-baseline-guest}。Bridge FAILURES零不能证明无调度问题。源码READY前files枚举/、settings读取DESK0/1，window/font也在前置路径；editor错误仍READY且介质无README，不能当FS读取成功对照。app_files逐ordinal同步LIST、fat32每次从raw0重扫/重复chain_length/slot_in整扇区读存在放大，但根目录很小尚非根因。实现候选只读QMP/既有符号与可信ABI捕获，在init杀死前的STARTING阶段记录四GUI初始化位置/FS客户端请求、FS当前op/caller/offset、block/xHCI状态、调度queue/perCPU/Bridge/FIFO；有界观测、原始字节与完整构建绑定、离线重放/负控。不能修改客体内存/寄存器/期限、伪造READY、用死后空进程代替首因。修正采集辅助bias尚未初始化的处理（不把宿主AttributeError当客体故障）。不改生产实现，明确停止/恢复观察会扰动时序；独立宿主复验后由协调者运行诊断，依据实际进展慢或RPC不返再派精确修复。Cursor手动，禁止CLI/VM自行执行。

## 可修改文件

- `cursor-works/src/p7/startup-capture/run_gui_startup_capture.py`
- `cursor-works/src/p7/startup-capture/contract.md`
- `cursor-works/tests/test_p7_startup_capture.py`
- `cursor-works/deliveries/P7STARTTRACE1.md`

## 定向验收

- `discover:cursor-works/tests:test_p7_startup_capture.py`

交付：`cursor-works/deliveries/P7STARTTRACE1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。
