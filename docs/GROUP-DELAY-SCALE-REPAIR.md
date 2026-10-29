# 群时延有限秒值的中间溢出修复

修复既有 `Network::group_delay` 的单位换算次序：先计算相位差/Hz差可能溢出，但最终再除 `2π` 的秒值仍可表示。原 `delay` 和 `delay-check` 继承这一误拒绝，现有公开包和文件路径现在都能消费完整有限结果。没有新 API、命令、JSON、RF 模型或文件格式。

## 手算反例与语义

合法的原始频率是 `[0,5e-324] Hz`，二端口 `S21` 为 `[1,1+j1e-15]`。这里的 `5e-324` 解码为 binary64 最小正数，`1e-15` 也按原始 binary64 输入取值。相位变化为 `atan(1e-15)`，因此已有割线定义给出的秒值是：

`−atan(y)/(2π Δf) ≈ −3.2213319106796408e307 s`

该秒值有限，原来的相位差/Hz差中间项却超出 binary64 最大值。修改前已复现 `delay` 和 `delay-check` 的 `group delay overflow`，新增回归中三项因此失败。这个合成边界验证当前有限输入合同，不表示真实仪器、器件或采样性能。

[scikit-rf 的官方定义](https://scikit-rf.readthedocs.io/en/latest/api/generated/skrf.network.Network.group_delay.html)是相位对角频率的负导数。本项目继续使用原来的解缠与离散估计：端点单侧、内部跨相邻两点的中心割线；非均匀网格同样使用原孔径。没有切换成另一个差分算法。

## 实际接收

先以项目指定工具链构建，再使用新输出路径：

```sh
moon build --target js --release --deny-warn
node tools/touchstone.mjs delay examples/delay-finite-seconds.s2p '{"input":0,"output":1}'
node tools/touchstone.mjs delay-check examples/delay-finite-seconds.s2p @examples/delay-finite-seconds-query.json NEW-SECONDS-REPORT.json
moon run examples/delay_finite_seconds --target js --release
moon run examples/delay_finite_seconds --target wasm-gc --release
```

文件报告包含两个约为 `−3.22133e307` 秒的原始估计，在 `[-5e307,0] s` 界限内为pass、退出0；改成最低0秒会正常输出fail报告、退出3。已有输出不会被覆盖。公开包例程实际解析原始文本，返回完整源矩阵、条件、秒值和既有报告；分别展示正/负延时及非均匀网格的中心精确零值。这是项目自编集成示例，不是外部采用证明。

## 修复与边界

只在原相位/Hz商为无穷时，先把相位差除 `2π` 再除 Hz 跨度；普通有限商保持原计算路径与输出。该溢出条件下，相位差不可能小到再除 `2π` 就下溢：Hz跨度至少是一个正 binary64，而溢出的相位/Hz商已经超过最大有限数。最终仍执行原有有限秒值检查。

- 相同跨度、虚部 `1e-14` 的最终秒值本身已超出范围，仍报 `group delay overflow`；没有夹取或伪造零值。
- 仍需至少两个频点，所选完整 S 迹线的任一点都不能为零；即使零在报告选区外也报错。非法端口、频率和秒限沿用旧错误。
- `delay-check` 仍先计算全迹线再选原点，保留孔径、正/负/零秒、精确界限比较、极值首个见证、完整计数及fail优先于覆盖不足；空选区不能通过。
- DB/RI/MA、NF/Gamma/GT、参数/参考/噪声/元数据、采样预算和其他 RF 算法保持。原相位混叠限制仍在，没有仪器等价、连续带宽或全binary64舍入切点保证。

## 独立验收入口

独立预期先于实现冻结：100位 Decimal 使用输入 binary64 的精确值、显式数学π及四项交错 `atan` 级数，其下一项余量小于 `2e-136 rad`。非均匀 `[0,tiny,3tiny]` 上的 `[0,y,0]` 相位源给出 `[-M,0,+M/2]`，不是从库输出生成真值。

`group_delay_scale_test.mbt` 在 JS/Wasm-GC 验证数值、全报告和保留错误；直接相关的旧解缠与限值测试继续验收。`tools/verify-delay-finite-seconds.py --evidence FRESH_PATH` 读取两个后端的完整公开包输出，再经真实文件 CLI 消费任意原始文件，核全数组、全部报告字段/孔径/计数/极值、0/3/4/2退出与输出保护。普通完整旧输出仅用作兼容控制，另用四分之一圈/MHz手算核其数值。

CI 必要步骤为 `Consume finite group-delay seconds from package and files`。all-target检查不算native执行；本轮不在本地重跑未改的旧科学生成器。初次探针漏传必需端口选项的脚本错误与纠正后的真实缺陷证据分别保存，没有把脚本失败冒充产品缺陷。
