# MoonTouchstone

[项目仓库](https://github.com/guolei-dev-2/moonbit-touchstone) · `guolei-dev-2/touchstone@0.3.0` · MIT

MoonTouchstone 是 MoonBit 原生射频网络数据处理库。它把 Touchstone 文件中的频率、参考阻抗和复数矩阵变成可计算的网络，提供参数变换、差分链路、噪声分析、采样频段判定与理想单频匹配，供射频工程、互连开发和教学工具使用。

当前仓库维护与申报账号为 **guolei-dev-2**。原实现来源 **guolei-dev**、贡献者版权及 Git 作者历史继续保留；当前仓库归属不改变原实现的作者归属。

## 功能

| 任务 | 已实现能力 |
| --- | --- |
| 文件读写 | Touchstone 1.0/1.1/2.0/2.1，RI/MA/DB，Hz–GHz，1–32 端口，全/上下三角及二端口顺序；保存 Information、噪声和模态元数据 |
| 网络变换 | S/Y/Z 及适用二端口 H/G/ABCD/T 互转，正实参考重归一化，端口选择、级联、已知左右夹具去嵌入和复 Γ/Ω 负载端接降维 |
| 混合模 | 指定不重叠差分对，S/Y/Z 单端与模态互转，成对 D/C 及未配对 S 端口，SDD/SDC/SCD/SCC 与三种功率波 CMRR |
| 带噪网络 | 二端口噪声参数与 Haus-Adler 相关矩阵互转、插值、级联、双侧去嵌入，Γ/物理复 Ω 源的 NF 及噪声圆 |
| 射频指标 | 回损、插损、VSWR、群时延，互易/无源诊断，K、μ/μ′、MSG/MAG、稳定圆/增益圆及实际终端传输功率增益 GT |
| 采样判定 | 多频段限值、通带波动、群时延与 NF 上限，保留原点、极值、覆盖和无法判定状态；GT 有逐点 CSV、字节/条件回执与复核 |
| 文件互操作 | 原频点闭 Hz 频段导出、完整单端文件导出、端接后的 S 文件；双原始 S 文件严格对照并保留双方输入身份和复差见证 |
| 匹配综合 | 单设计点理想无损单并联开/短路短截线，主周期内两条电长度解或已匹配连续距离族，并由现有 Network 正向消费 |

格式解析、矩阵和 RF 计算均在 MoonBit 中实现。Node.js 只负责文件、参数、散列和编译桥接；Python 用于开发期独立验值，库运行不依赖 Python。

## 从源码运行

工具链版本见 [.moonbit-version](.moonbit-version)，文件 CLI 使用 Node.js 24。

```sh
git clone https://github.com/guolei-dev-2/moonbit-touchstone
cd moonbit-touchstone
moon build --target js --release --deny-warn
node tools/touchstone.mjs inspect examples/attenuator.s2p
node tools/touchstone.mjs rf-convert examples/attenuator.s2p '{"parameter":"ABCD"}'
moon run examples/rf_03 --target js --release
moon run examples/rf_03 --target wasm-gc --release
```

自有公开包导入路径：

```moonbit
import {
  "guolei-dev-2/touchstone" @rf,
}
```

`parse(text, ports=2)` 返回 `Document`。`network_only()` 返回还原的单端确定性 `Network`；带噪处理使用 `Document` 方法传播噪声。`raw_network()` 是文件原始矩阵，混合模输入的原始坐标仍按模式描述符解释。完整签名见 [生成接口](pkg.generated.mbti)，调用约定见 [API 指南](docs/API.md)。

## 文件消费与报告

```sh
node tools/touchstone.mjs metrics examples/attenuator.s2p '{"input":0,"output":1}'
node tools/touchstone.mjs noise examples/noise-limits.ts '{"source_mode":"impedance","source_ohms":[100,0]}'
node tools/touchstone.mjs noise-check examples/noise-limits.ts @examples/noise-limit-query.json
node tools/touchstone.mjs single-file examples/single-file-source.ts '{}' NEW-SINGLE.ts
node tools/touchstone.mjs --help
```

上面 NF 采样例在 4 MHz 超过 2 dB 上限，输出有效的 `fail` 报告并退出 3。采样判定的退出码为 pass=0、fail=3、inconclusive=4；输入/数学/IO 错误为 2。`gain-review` 的不匹配为 5；`s-compare` 的超限/不兼容分别为 3/4。文件变换输出 Touchstone，分析命令输出 JSON；有输出路径时独占创建文件，保留已有输出和源文件。

| 工作流 | 说明与可运行入口 |
| --- | --- |
| 单端与频段文件 | [single-file](docs/SINGLE-ENDED-FILE.md)、[crop](docs/CROP-FREQUENCIES.md) |
| 端接文件与增益 | [terminate-file](docs/TERMINATE-FILE.md)、[GT 条件与报告](docs/GAIN-CHECK.md)、[回执复核](docs/GAIN-RECEIPTS.md) |
| 源相关噪声系数 | [物理 Ω 源 NF](docs/NOISE-IMPEDANCE.md)、[NF 采样上限](docs/NOISE-CHECK.md) |
| 延时与矩阵对照 | [群时延限值](docs/GROUP-DELAY-CHECK.md)、[双 S 文件对照](docs/S-COMPARE.md) |
| 匹配与显示 | [理想短截线](docs/SHUNT-STUB.md)、[一端口指标](docs/ONE-PORT-METRICS.md) |

所有 [examples](examples) 下的公开包例程都导入当前命名空间。例程覆盖单端/模态、噪声、GT、限值、文件导出和匹配；既可运行 JS，也可运行 Wasm-GC。确定性 Network JSON 与保留噪声/模态/Information 的完整文件是不同表示，按各命令约定使用。

## 单位与适用边界

频率为 Hz，阻抗为 ohm，Y 为 siemens，矩阵行优先 `S[out,in]`。ABCD 满足 `[V1,I1]ᵀ = A[V2,-I2]ᵀ`，T 满足 `[b1,a1]ᵀ = T[a2,b2]ᵀ`；ABCD/T 是分析表示，写 Touchstone 前须转回合法文件参数。

差分对内参考须相等，跨对可不同；D、C 有效参考分别为 2Z0 和 Z0/2，文件 Reference 仍保存原单端参考。balanced/input/output CMRR 是三种功率波幅度比，不能直接当作差分放大器电压增益 CMRR。NF 的源 Γ 使用独立 `noise_reference_ohms`，与网络端口参考分别记录。

当前模型使用有限 double、频率不变的正实参考，预算 10 万频点、200 万复数值和 64 MB 文本。奇异/病态矩阵、不可实现噪声或域外源明确失败；无穷损耗、无定义 VSWR 和 GT 特殊状态由字段/标志表示。噪声单记录按常量处理，多记录不外推；没有噪声记录的夹具表示零附加噪声，不自动推断热噪声。

采样判定只约束原始离散点，不能认证点间连续频带。无源 `boundary` 包含无损及容差边界，不能视为严格合格。理想单频匹配不提供微带毫米、双短截线、Q/带宽优化；本库不提供复参考功率波、未知夹具提取、仪器校准、全频因果性或器件认证。完整约定见 [RF 0.3](docs/RF-0.3.md) 和 [范围](docs/SCOPE.md)。

## 验证与来源

```sh
moon fmt --check
moon check --target all --deny-warn
moon info
moon test --target js --deny-warn
moon test --target wasm-gc --deny-warn
moon package --frozen
```

[verify 工作流](.github/workflows/ci.yml)运行严格检查、两个后端的测试与公开包消费者、实际文件链、独立数值参考及模块封包。CI 身份回执记录实际模块、仓库、工具链与源码散列；某次远端结果以同仓库、同一提交的真实 run 为准，见 [CI 说明](docs/CI.md) 与 [CI 计划](CI-PLAN.md)。

历史科学回执按原日期、输入与适用范围保留，职责和误差单位见 [验证记录](docs/API.md#验证职责与历史记录)。Johanson 与 NXP 的有限厂家文件案例不代表全部偏置、器件认证或客户采用；未确认再分发授权的厂家原件及完整数值导出不随包分发。

项目使用 MIT，版权声明见 [LICENSE](LICENSE)，原作者与贡献者历史保留。标准及参考包括 [IBIS Touchstone 2.1](https://www.ibis.org/touchstone_ver2.1/touchstone_ver2_1.pdf) 与 [scikit-rf](https://scikit-rf.readthedocs.io/)；第三方授权和来源见 [THIRD-PARTY](THIRD-PARTY.md) 与 [SOURCES](docs/SOURCES.md)。不主张经典 RF 算法原创或生态唯一。

正式项目介绍见 [PROPOSAL](PROPOSAL.md) 与 [账号对应附件](guolei-dev-2-touchstone-申报书.md)，当前维护/申报元数据见 [SUBMISSION](SUBMISSION.json)。
