# G6POOL1 交付

修复 G6 复用的 P5 物理检查器：不再假定三个服务均使用静态池。通过 kernel_storage_profile.verify_profile 验证构建配置和源码，取得静态池数；动态池必须与内核 DYNAMIC_PHYSICAL/DYNAMIC_TABLES 记录一致，落在已分配 arena 内，32 页逐页具有精确 supervisor RW/NX/WB 映射，且不得与内核或其它服务池重叠。原逐级页表遍历仍限制在各自 32 页池内。

本机实测：python -B -X utf8 -m unittest tests.test_services_pool_ownership tests.test_compiler_guest_runner，20 tests，0 skip，全部通过。覆盖静态旧配置、动态配置、身份/容量/边界/重叠、每页映射权限反例。

此前真实运行 run-662c6cec8a01 保持失败，不改写回执。本修改仅完成检查器适配，G6 同盘双启动尚待新检查器实际运行，不声称整个 L3 完成。


## AI交付 2026-10-23T14:57:43+00:00 · codex-mcp-839d838dd7b04cc5

实际文件已修改；20 tests/0 skip 本机通过，静态/动态池归属严格负控；原真实失败回执保留，待独立复验和新双启动。
