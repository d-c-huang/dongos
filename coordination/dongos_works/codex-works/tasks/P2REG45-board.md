# P2REG45 — P2既有服务启动与桌面重建回归夹具接续

负责人：codex。状态：待领取。

P2LEDGER44运行声明的回归发现两项旧夹具编译失败：test_service_launch抽取的生产服务函数已调用large_request但夹具未提供；test_desktop_recreate的独立memory stub缺map_framebuffer。两测试不执行本轮ledger生产实现，保持原原生正负判定、拒绝放宽检查或skip，仅补齐新已集成接口的明确模拟边界，暴露并断言必要调用。不得修改生产源码/其它测试，不声称替代ledger实际页表测试。通过独立正式两测试后集成。

## 可修改文件

- `tests/test_service_launch.py`
- `tests/test_desktop_recreate.py`
- `codex-works/deliveries/P2REG45.md`

## 定向验收

- `module:tests.test_service_launch`
- `module:tests.test_desktop_recreate`

交付：`codex-works/deliveries/P2REG45.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。
