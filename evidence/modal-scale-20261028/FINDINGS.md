# 第24轮：混合模指标有限dB被中间模长溢出破坏

在同一混合模指标消费者中，先确认零/零等四种CMRR状态原本正确，无需修改合同。随后从源码发现先求线性模长再取log会丢掉本可表示的有限dB。编辑前3次实际Node文件调用复现：合法有限复分量四端口能解析；Sdd21=Scc21=1.5e308+j1.5e308的balanced CMRR应精确0 dB，旧入口却退出0并给`cmrr_state="finite"`、`cmrr_db="NaN"`及差分损耗`"-Infinity"`。普通.5+j.5控制正常；BASELINE/原输入/原日志保留。

实现只改mixed_mode.mbt的损耗/CMRR对数模长消费：原有限模长路径保持，溢出时用分量缩放求log，零值仍为None并维持原四态。没有改Complex::magnitude、模式变换、参考、解析、GT/helper、噪声或Node，没有新API/命令/格式，不增加epsilon或缩小合法域。

实际修复后首个运行验收通过：新3项API测试在JS/Wasm-GC/native各3/3；9个实际Node文件请求、7项消费者检查通过。标准库Decimal100直接平方范数及比值求log作为独立预期，核数值类型和2e-10 dB绝对误差、三种定义、四项损耗及零状态。原反例现为数值0 dB和有限−6166.532125137754 dB；普通输入完整输出与修复前字节一致。旧20/22/23集合和其他已通过旧测试未重跑。

缓存隔离先查实共享SDK lib/core/_build和registry。为遵守禁止写原SDK/旧报告，读取复制同版本工具到本轮toolchain，MOON_HOME、TEMP/TMP、XDG_CACHE_HOME、LOCALAPPDATA和APPDATA均限当前报告，Node编译缓存关闭，Python字节码关闭，无update/install。初次复制过度排除了该版SDK必需的stdlib bundle，首次release build报缺math.mi，尚未执行产品测试。保留失败日志与CHECKS条目，随后只读复制648个必需bundle文件到本轮副本，未复制旧锁/构建数据库；修正构建和首次实际三后端/消费者运行均通过。这不是删掉失败记录或把环境失败伪称产品修复。

工具与bundle复制SHA、实际缓存路径和最终原SDK只读身份核对见TOOLCHAIN-CACHE-ISOLATION/STDLIB-BUNDLE-SNAPSHOT/CACHE-ISOLATION-AUDIT。它们只作来源证据，SDK二进制不放进产品源码ZIP。所有新编译由本轮副本执行；全局SDK、旧报告和旧封存件不写入。

README、RF约定、范围、可运行合成文件及29行申报书介绍真实功能/边界，同名附件相同字节。新指南说明超大有限分量是数学尺度反例，不代表无源/实际器件测量；功率波CMRR定义不变。Keysight官方balanced比值与scikit-rf模态顺序只作为既有定义参考，不是本轮执行的外部oracle；Mooncakes检索未确认额外相关包，不作唯一性宣称。

最终接口/源码/编译身份、严格编译/格式、本地模块包及逐文件ZIP读回以RESULT/CHECKS/DELIVERY-CHECK为准。没有推送、发布、比赛提交、账号/作者/全局SDK/STATE修改或其他聊天消息；不新增厂商输入或连续频带/全输入正确性承诺。完成有限修复和必要验收后停止。
