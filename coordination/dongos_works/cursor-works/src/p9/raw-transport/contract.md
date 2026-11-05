# P9 有界 ASCII 回执传输

只封装现有 binary BEGIN/CASE/END。每行严格为 `P9LOG1 ssss ll hex\n`：四位小写十六进制零起序号，首行长度40（64字节），其余20（32字节），payload为原始内存字节的小写hex。首行144字节，后续80字节；1..256案例对应3..258行，总量最多20704字节。无CR、空格变体、前后噪声、重复、跳号、截断或额外记录。真实Dong编码器使用固定数组，避免字符串slice静态指针破坏PIE链接。输出失败锁存，consumer返回2，不继续宣告完成。

corpus_entry.asm实际将日志送往0x70 syscall，CORPUS_HOST才转独立C边界；原七寄存器case syscall映射不变。生产services.dg的0x70限制4096B并copy_in后交给services_write_bytes；kernel/services_run.asm维护4096B环形缓冲，UART缺失/超时会丢输出但仍返回0。因此完整捕获必须来自外部且包含全部专属行；成功syscall不能证明完整交付，256例不能依赖环形缓冲保留。缺行在严格检查中拒绝。未添加内核捕获、启动清单或执行OS/VM。

构建只生成一个实际链接的PIE ELF，归档真实编译sources及五个transport实现，后者SHA集合规范序列化后写入真实编译guest源注释，故原BEGIN binding也覆盖编码器、解码器和builder。外层transport-manifest.json绑定该集合与内层原receipt manifest，调用者必须提供可信外层SHA及generation。来源文件、生成data、assembly、ELF、corpus和原始回执全部由原验证器复核。不存在参考ELF替代实际执行档案的做法。

离线verify_log只接收bytes，最多20704B；文件读取有界，manifest严格schema及重复键拒绝；解码后交给既有verify_receipt，依然核对每个raw return、顺序、generation、终态、外部退出码/超时。execution仅host，guest无条件拒绝；文本和归档不能证明归档ELF在客体执行，结果始终guest_verified=false。

本地实际测试2项/30.418s/0skip通过，证据code/build/test/p9-corpus-log/run-62a1c33629cc。debug/release真实Dong→NASM→独立C宿主运行，以独立Python struct/hex oracle逐字节比较；每模式正常12例、真实坏体错case/漏END/混generation均正常编译运行exit0后被验证器拒绝，错误返回/输出失败分别exit3/2。另真实执行1例及256例边界，后者精确20704B。全部前缀截断、噪声、CRLF、大写、乱序、重复、坏长度、raw return、源快照/ELF篡改、退出/超时/guest请求拒绝。首轮PIE字符串重定位失败记录保留run-d816eb2d383f；修复后通过。独立审查和正式复验尚待完成，不宣称P9或真实客体采集完成。
