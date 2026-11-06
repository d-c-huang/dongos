

## AI交付 2026-11-06T06:09:15+00:00 · codex-mcp-e30a159488a44d74

真实普通USB构建在默认hardware_profile精确契约失败：当前Windows core.autocrlf=true造成4处CRLF。服务策略已恢复为git HEAD blob逐字相等的LF，无逻辑变更，根.gitattributes固定唯一路径code/services/lib/hardware_profile.dg text eol=lf（工作区跨机维护）。未改变USB_ONLY/FAT_AUDIT_BYTES或严格验证器。宿主现有test_usb_only_profile/test_usb_profile_packaging共7项0skip，31.855s通过；真实native证据run-6a50fef43b22。冻结原失败日志保留code/build/test/p6-bkl-integration/run-20261106/usb-build.log；新source-manifest-lf记录唯一字节调整，完整构建重跑中。独立只读审查另行完成；正式复验前不宣称验收。
