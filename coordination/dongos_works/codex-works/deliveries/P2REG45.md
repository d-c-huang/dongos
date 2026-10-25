# P2REG45 交付

2026-10-24：修复两项陈旧宿主夹具与已集成生产接口的脱节。

- 服务启动原函数已经调用 large_request；夹具新增明确模拟边界，要求 memory stage 已提交且未失败。没有模拟实际大页事务通过。
- 桌面重建 memory stub 新增 map_framebuffer，继续调用原独立 C dt_device 检查 compositor、VA、PA 和 rounded prefix 长度。不模拟实际 WC 授权。
- 原生产片段、正常场景、错误源码及返回值断言保持；不加 skip。

本机 `python -B -X utf8 -m unittest tests.test_service_launch tests.test_desktop_recreate`：2 tests / 0 skip / 44.899 秒通过。
原生证据：build/test/service-launch/run-0ad551de21ab、build/test/desktop-recreate/run-d8c3c1a15d12。
尚待协调器独立复验；此卡不覆盖真实 ledger/硬件/客体运行。


## AI交付 2026-10-24T09:07:37+00:00 · codex-mcp-14ca67a3341042c4

已修复旧launch/desktop夹具接口缺失，保留真实生产片段和全部原坏源码断言。本机2项零skip/44.899秒通过；生产源码未在此卡更改。交付P2REG45.md已落盘，待独立复验。
