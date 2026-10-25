# LM10 — P2简单数据：runtime_cache八种错误码中文对照

负责人：lmstudio。状态：待领取。

只生成两文件，不改测试/生产代码。fixture为JSON，严格顶层schema=1,module='mm.runtime_cache',errors数组；恰好8项，每项严格字段name,code,meaning。code为0x十六进制字符串，meaning为简短准确中文，不声称这些错误已在真机验证。生产常量依据：Invalid=0x06150001(参数/状态无效)、Authority=0x06150002(可信CPU/根/权限前提不满足)、Forest=0x06150003(页表森林与授权别名闭包不符)、HardwareState=0x06150004(PAT/MTRR等实际硬件状态不符)、Held=0x06150005(事务资源须保持持有)、Deadline=0x06150006(截止期限)、Capacity=0x06150007(容量不足)、Storage=0x06150008(调用方存储范围/别名等不合法)。用于P2 C/D后续诊断显示，不增加枚举、不改名、不改数字。交付说明未运行测试，由Codex对照当前生产源码逐项独立验证。依赖LM9验收后再运行，同一时刻只执行一项本地模型任务。

## 可修改文件

- `lmstudio-works/fixtures/p2-cache-errors.json`
- `lmstudio-works/deliveries/LM10.md`

## 定向验收

- `discover:lmstudio-works/tests:test_p2_cache_errors.py`

交付：`lmstudio-works/deliveries/LM10.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。
