# MoonTouchstone

[项目仓库](https://github.com/guolei-dev-2/moonbit-touchstone) · `guolei-dev/touchstone@0.3.0` · MIT

MoonBit 原生 Touchstone 1.0/1.1/2.0/2.1 射频网络变换、混合模/噪声级联与采样频段分析库。输入是带频率、参考阻抗和物理单位的复数矩阵；计算核心包括参数互转、模态变换、噪声与射频稳定性。


2026-10-23 复核修复见 [复核记录](REVIEW-20261023.md)，包含上一轮漏检的反例和本轮验证入口。
2026-10-27 [上限端口与边界加固](docs/HARDENING-20261027.md)：31/32端口混合模及无源性独立回归55次请求通过，JS/Wasm-GC各31项通过；数学实现和公共API保持不变。历史厂商样本及368/1103回执未重跑。
## 0.3.0 新增

新增[群时延采样限值](docs/GROUP-DELAY-CHECK.md)：`Network::check_group_delay`与`delay-check`按Hz闭区间、SI秒界限给出采样判定、原点极值和全部估计的实际差分孔径。复用旧`group_delay`定义，全迹线至少两点且所选S全程非零；0与负秒限有效，fail优先于覆盖不足。没有新增解缠、平滑、插值或连续频带认证，旧`delay`输出不变。

2026-10-29 本地拓展：[单并联理想短截线匹配](docs/SHUNT-STUB.md)。`synthesize_shunt_stub` 在单设计点、共同正实 Z0 下显式选择开路或短路，返回主周期内两条电长度解或精确已匹配的连续距离族，并区分纯无功无解、非法输入及数值限制。`moon run examples/shunt_stub_match --target js`（或 `wasm-gc`）用当前 Network 的 ABCD、级联和 Ω 端接实际消费结果；独立解析 ABCD 核对手算及复负载。只给弧度/导波波长比例，不提供微带毫米、双短截线、Q/带宽优化或性能承诺。

20轮[噪声源功率余量修复](docs/NOISE-SOURCE-REPAIR-20261028.md)：`noise_figure`复用既有精确复分量余量，修复近单位圆合法源的噪声系数严重偏差及相邻域外源误接受。独立高精度公式核对320.34118/164.77469 dB反例；新3项测试三后端各通过，6次实际文件CLI/5项检查通过，普通匹配源完整输出保持。公共API、噪声相关矩阵/插值/圆及其余RF算法不变。

17轮[混合模信息行修复](docs/MIXED-INFORMATION-REPAIR-20261028.md)：修复`mixed`文件转换漏传合法Information信息行的问题。3行信息的实际反例已复现，修复后8个Node进程/6项定向检查通过；网络/模态顺序和无信息输入文本保持，公共API及RF算法不变。第16轮相邻项已在本轮闭环，旧回执不改写。

16轮本地拓展：[显式端接后导出Touchstone](docs/TERMINATE-FILE.md)。独立`terminate-file`把带复Γ/Ω负载的多端口降维结果写成可继续消费的单端S文件，保留信息行，明确拒绝无法传播的噪声记录。提供四端口→二端口→GT回执的可运行文件示例；主验收27个CLI用例/19项检查、6个独立全四端口方程GT对照通过。旧`terminate` JSON、数值算法和公共API保持。

13轮本地拓展：[GT逐点CSV审阅](docs/GAIN-CSV.md)。`transducer_gain_samples_csv`与`gain-csv`导出闭频段内每个原始采样点，保留五种GT状态、限值标志和逐点/整段判定。新7项测试三后端各通过，27个实际CLI进程/29项消费者检查通过；旧数值、报告及回执协议保持。

12轮本地拓展：[GT回执与复核](docs/GAIN-RECEIPTS.md)。可选`gain-record`把实际输入字节、有效Γ/Ω条件和采样报告存为回执，`gain-review`检查输入身份并重新计算比较；成功复现fail仍是指标失败。43个实际CLI进程、32项工作流检查通过，旧数值/报告算法与公共库API不变。

11轮本地拓展：[实际终端GT采样限值报告](docs/GAIN-CHECK.md)。`gain-check`同时支持Γ/Ω条件，给出通过/失败/无法判定、状态计数、最差原始频点和覆盖说明；正确区分零功率、正功率上/下溢与奇点。新测试三后端各8项、独立39次请求/27份报告比对通过，05—10数值实现不变。

10轮本地拓展：[直接以复阻抗Ω查询GT](docs/IMPEDANCE-GAIN.md)。新增`transducer_gain_impedance`及独立CLI命令，接收物理源/负载Ω，保留转换为Γ时可能丢掉的小正电阻信息；附文件/纯MoonBit示例。新功能三后端各8项、最终独立55次请求/52点通过，原Γ接口及05—09实现保持。

本地拓展：[实际源/负载传输功率增益GT](docs/TRANSDUCER-GAIN.md)。`Network::transducer_gain`与`transducer-gain` CLI消费复Γs/Γl，区分有限、精确零、奇点及正功率的上/下溢，并保留可表示的dB值。提供合成文件与纯MoonBit示例；这是实际终端增益分析，不替代稳定性判据。

09轮[匹配边界修复](docs/MATCHING-REPAIR-20261028.md)直接从复分量保留近单位圆的正功率裕量，修复错误增益与域外负载误接受，公共API不变。相关GT测试三后端各10/10；66次新边界请求、41个有效点及3次实际文件CLI消费通过，厂家模型只新增两组各3点的GT核对。

2026-10-28 [格式极值修复](docs/FORMAT-REPAIR-20261028.md)修复旧版Y/Z/H/G归一化中间溢出及巨大度数周期丢失。相关解析/写出测试JS/Wasm-GC/native各10/10，独立Fraction与元数据消费者70次请求通过；公共API保持兼容。

2026-10-28 [RF极值修复](docs/RF-EXTREME-REPAIR-20261028.md)修复极大K下MAG误归零、复阻抗端接的溢出/Γ极点误拒绝及小Rn被抹零。相关RF回归在JS/Wasm-GC/native各8/8通过，另有60次独立消费者请求；没有重复历史全套或厂商输入。

2026-10-28 [数值尺度修复](docs/NUMERIC-REPAIR-20261028.md)修复有限复数商的中间溢出、复数主元误判及大尺度消元误拒绝，公共API保持兼容。JS/Wasm-GC各38/38、新增native数值回归及独立Fraction/scikit-rf定向检查通过；历史31/55及厂商输入未重跑。

- 指定差分对的单端 ↔ 混合模 S/Y/Z，支持成对 D/C 和保留单端 S，正确计算差分/共模参考阻抗；文档模态顺序还原及 SDD/SDC/SCD/SCC/CMRR。
- Haus-Adler 噪声相关矩阵，带噪文档频率插值、级联、左右夹具去嵌入、任意合法源反射的噪声系数与噪声圆；网络和噪声同时变换。
- ABCD/T 链参数、任意复反射或复阻抗负载端接降维，Rollett K/|Δ|、μ/μ′、MSG/MAG、稳定圆和增益圆。
- 保留阻抗重归一化、互易/无源诊断、群时延、损耗/VSWR、多频段采样限值与通带波动；不静默抛弃文件元数据。

全部格式与数学运算在 MoonBit，Node 仅做文件/参数/文件散列及桥接；库运行不依赖 Python。完整约定、CLI 和独立对照见 [RF 0.3](docs/RF-0.3.md)。

远端验证的命令、固定版本与回执约定见[CI说明](docs/CI.md)；历史本地回执不代替同一提交的实际 GitHub run。

[GT文件审计链持续验收](tools/verify-gain-file-chain.py)在CI中新生成四点网络，以独立功率真值贯通`gain-record`、`gain-review`与`gain-csv`，核对原始字节、零/奇点、篡改拒绝和输出占用保留。它补齐实际文件消费保证的自动验收，不增加RF能力或改变协议。

[五端口导出文件链](tools/verify-termination-chain.py)另以新鲜有理数网络、完整原端口波方程和独立字节解码，持续核验非相邻端口保留顺序、信息/参考、再消费GT，以及原有主动端接、噪声拒绝和IO保护；没有新增端接算法或格式。

## 构建与运行

工具链固定在 [.moonbit-version](.moonbit-version)，Node.js 24 用于文件 CLI。

```sh
moon update
moon build --target js --release --deny-warn
node tools/touchstone.mjs inspect examples/attenuator.s2p
node tools/touchstone.mjs rf-convert examples/attenuator.s2p '{"parameter":"ABCD"}'
node tools/touchstone.mjs stability examples/attenuator.s2p
node tools/touchstone.mjs noise examples/noise-source.s2p '@examples/noise-source-options.json'
node tools/touchstone.mjs mixed examples/mixed-information.ts '@examples/mixed-information-options.json' NEW-MIXED.ts
moon run examples/rf_03 --target js
moon run examples/rf_03 --target wasm-gc
node tools/touchstone.mjs transducer-gain examples/power-gain.s2p '@examples/power-gain-options.json'
node tools/touchstone.mjs transducer-gain examples/power-gain.s2p '@examples/power-gain-near-circle.json'
node tools/touchstone.mjs transducer-gain-impedance examples/power-gain.s2p '@examples/power-gain-ohms.json'
moon run examples/power_gain_ohms --target js
node tools/touchstone.mjs gain-check examples/power-gain.s2p '@examples/gain-check-gamma.json'
node tools/touchstone.mjs terminate-file examples/loaded-four-port.ts '@examples/terminate-four-port.json' NEW-TWO-PORT.ts
node examples/terminate_file_demo.mjs NEW-OUTPUT-DIRECTORY
node tools/touchstone.mjs gain-csv examples/power-gain.s2p '@examples/gain-check-ohms.json'
moon run examples/gain_csv --target js
node tools/touchstone.mjs gain-review examples/power-gain.s2p '@evidence/gain-receipt-20261028/receipt-fail.json'
moon run examples/gain_check --target js
moon run examples/power_gain --target js
```

纯 MoonBit `rf_03` 示例展示新接口，不依赖 Python/文件宿主。已有频段用法：`moon run examples/band_check --target js`；故意设置不通过的回损规则会输出 fail，这是有效判定而非崩溃。

## API 与物理约定

公共接口见 [pkg.generated.mbti](pkg.generated.mbti)。根包导入 `"guolei-dev/touchstone"`；`parse(text, ports=2)` 返回 Document，`network_only()` 返回单端网络视图；噪声继续保留在 Document，带噪运算应调用 Document 的接口。`raw_network()` 仅表示文件原始矩阵，不应将它当成单端矩阵。

查看一端口阻抗扫频的回损与VSWR，可运行`moon run examples/one_port_metrics --target js`。这个[公开模块示例](examples/one_port_metrics/main.mbt)读取有限Z参数，展示匹配、全反射、主动反射和复阻抗；`vswr_state`与无穷标志帮助应用区分没有有限数值的原因。相同文本可交给现有`metrics`文件入口；用法、解析公式和独立消费者核对见[一端口指标](docs/ONE-PORT-METRICS.md)。

实际调用、错误和验证分工见 [API与证据约定](docs/API.md)：转阻抗使用 `network.convert("Z")`，失败通过 `raise` 传播；理想短路可以表示为零阻抗，理想开路转有限Z则遇奇点。可运行的纯MoonBit消费示例为 [rf_03](examples/rf_03/main.mbt)。

频率 Hz、阻抗 ohm、Y 为 siemens，行优先 `S[out,in]`。ABCD 为 `[V1,I1]ᵀ = A[V2,-I2]ᵀ`，T 为 `[b1,a1]ᵀ = T[a2,b2]ᵀ`。ABCD/T 是 API/JSON 分析表示，不是合法 Touchstone option line 参数。

差分对内两端单端参考阻抗必须相同，跨差分对可不同；例如 50/50 与 75/75。D 参考为 2Z0、C 为 Z0/2；不等阻抗对先显式 renormalize。文件 Reference 与有效模态参考的区别及变换顺序见 RF 指南。

混合模指标的CMRR可选择balanced/input/output三种功率波幅度比；零比值分别给出undefined、positive_infinity或negative_infinity，有限值为数值dB。对于复分量有限、线性模长中间溢出而dB仍可表示的输入，CMRR和模态损耗使用稳定对数计算。可运行的`modal-metrics`文件例程及适用边界见[混合模dB计算](docs/MODAL-SCALE-REPAIR-20261028.md)。

已知可逆左右夹具的去嵌入支持无噪声记录、S21精确为零的有限DUT，例如截止点或隔离网络；输出仍可交给`metrics`区分无限插损。非零传输保留原计算路径，夹具奇异和真正恢复极点仍报错。可运行文件用法及噪声/链表示边界见[截止频点去嵌入](docs/DEEMBED-ZERO-20261028.md)。

1–32 端口、有限 double、正实且频率不变的参考阻抗；复负载端接不等于复参考阻抗功率波定义。奇异/病态矩阵、失稳端接和不可实现噪声明确报告；不靠任意扰动伪造结果。数据预算与完整验收条件见 [SCOPE](docs/SCOPE.md)。

无源性沿用既有 `I−SᴴS` 的移位Cholesky严格正定测试，默认绝对容差ε=1e-9。`boundary` 包括无损边界及容差带内的轻微负特征值，不能自动算严格无源合格；完整三态条件见 [RF约定](docs/RF-0.3.md#无源性与容差)。

## 独立验证与证据

```sh
moon fmt --check
moon info
moon check --target all --deny-warn
moon test --target js --deny-warn
moon test --target wasm-gc --deny-warn
moon package
```

2026-10-23历史回执以scikit-rf/NumPy独立对照混合模、噪声级联/去嵌入、参数、复负载和稳定性；其368请求/1103断言保持原日期。随后55请求的上限端口回归包括30个无源案例、9组混合模正反向（18请求）和7个预期拒绝，参考职责与S/Y/Z误差单位见 [API与证据约定](docs/API.md#验证职责与历史记录)。后续数值/RF/格式修复和GT拓展各自的定向证据见上方记录，没有重跑这些历史集合。编译后端数量不等于操作系统数量或全部数值输入均已验证。

既有 [Johanson 厂家公开 S2P 案例](docs/PUBLIC-SAMPLE.md) 包含 1551 频点，历史回执保留日期；2026-10-27 另补 [NXP BFU530W 第一方输入](evidence/public-breadth-20261027/README.md)，仅选 3.3V/1mA 一份文件的98频点，对当前0.3.0 CLI 的 S 参数、S→Y及写出重读逐点独立核对。由此有两家器件厂商的有限输入证据，不把测量仪器品牌计为厂商，也不声称全部偏置、全部厂商或新测量通过。未确认再分发权的原包、原文件和完整数值导出不随包附送。离散采样限值不代表连续频带保证、器件认证或客户采用。

标准与参考：[IBIS Touchstone 2.1](https://www.ibis.org/touchstone_ver2.1/touchstone_ver2_1.pdf)、[scikit-rf](https://scikit-rf.readthedocs.io/)，许可及来源见 [THIRD-PARTY](THIRD-PARTY.md) 和 [SOURCES](docs/SOURCES.md)。不主张射频算法原创或全网唯一。

## 复审交付

本轮 0.3.0 仅本地完成，没有推送、发布或修改报名表。旧版公开 CI 不能证明新代码的远端状态。[申报书](PROPOSAL.md) 与 [同名附件](guolei-dev-touchstone-申报书.md) 已统一；原上传附件是否误传须由报名记录核实，说明见 [REVIEW](REVIEW.md)。
