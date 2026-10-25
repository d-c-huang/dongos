# P8GOP1 — 真机E10的GOP分辨率回退与分支诊断

负责人：codex。状态：待领取。

用户真机图证S01加载器低跳板和镜像校验成功，S04报E10；原runtime3通过，runtime7独有display_mode强制1920x1080，实际桌面契约已支持800..1920x600..1080、width<=stride<=2048、RGB/BGR。修复为有界枚举<=256模式，优先最大有效像素面积（仍优先1080p），失败候选按次优重试，必要使用完整验证后的当前模式；每次Query buffer释放一次，FreePool失败停止；SetMode后检查实际Mode/Info/格式/范围/低4GB framebuffer和容量，不截断/不支持BLT-only或bitmask。800x600等fallback必须通过真实native回调与缺Free/坏排序/漏actual验证的实际坏体。efi新增GOP分支原因及完整64位数值诊断，失败仍在EBS前；不打印未验证buffer字段，不越界查Mode/Info。root实际VM验证1080p原模式与只暴露fallback的模式，独立定向测试0skip源稳定后验收/集成。保持USB-only profile、P8低跳板/EBS契约和kernel/services不变；H不在则仅准备待插回，不写其它盘、不格式化、不Git提交推送。

## 可修改文件

- `boot/display_mode.asm`
- `boot/efi_main.asm`
- `tests/test_display_mode.py`
- `tests/display_mode_probe.c`
- `tests/test_loader_graphics.py`
- `tests/loader_graphics_probe.c`
- `docs/loader-gop-fallback.md`
- `codex-works/deliveries/P8GOP1.md`

## 定向验收

- `module:tests.test_display_mode`
- `module:tests.test_loader_graphics`
- `module:tests.test_loader_console`
- `module:tests.test_loader_handoff`

交付：`codex-works/deliveries/P8GOP1.md`。独立工作副本中执行；不提交、推送、运行OS/VM或修改归属外文件。完成后提交交付，等待独立复验。
