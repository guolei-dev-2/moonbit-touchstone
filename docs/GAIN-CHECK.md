# 实际终端GT的采样限值报告

拿到Touchstone和一组源/负载条件后，除了看逐点GT，还常需判断指定频段是否达到要求、最差点在哪，以及奇点或缺少样本是否影响结论。11轮提供`gain-check`与`check_transducer_gain`，直接消费既有Γ或Ω两条GT结果；数值算法和旧命令保持。

## 文件工作流

```sh
moon build --target js --release --deny-warn
node tools/touchstone.mjs gain-check examples/power-gain.s2p '@examples/gain-check-gamma.json'
node tools/touchstone.mjs gain-check examples/power-gain.s2p '@examples/gain-check-ohms.json'
moon run examples/gain_check --target js
moon run examples/gain_check --target wasm-gc
```

第一个选项文件使用默认Γ匹配、1–2GHz、3–7dB限值，返回pass。第二个配置100+j20Ω源、25−j10Ω负载及4–7dB限值，刻意返回fail：最低值在原始点索引1、2GHz，约3.38585099433dB，理由below_minimum。两份配置的限值不同，分别演示通过与失败流程；不是把判定变化全部归因于终端改变。

命令输出根对象包含status、terminal_mode、reference_ohms、matching及report，回显实际使用的条件和参考阻抗。默认`terminal_mode:"gamma"`，source/load为可选`[real,imag]`且默认[0,0]；显式`"impedance"`时必须提供source_ohms/load_ohms。公共项start_hz/end_hz必填，至少一个有限minimum_db/maximum_db。两类终端键不能混用，未知键、错误单位键及无关夹具文件均报错。

| 退出码 | 含义 |
|---|---|
| 0 | 原始采样点通过 |
| 3 | 已知采样点超限，报告正常输出 |
| 4 | 没发现超限，但覆盖、样本或奇点使结论无法确定 |
| 2 | 配置、格式、网络转换、终端域或文件IO错误 |

添加第四个参数可保存JSON，即使exit3也会保存失败报告；已有文件拒绝覆盖。CLI使用Document::network_only()的单端网络视图并回显其参考阻抗，不改写原始文件元数据。解析、视图或S参数转换失败仍报错2；不能提供GT迹线的错误不会被伪装为报告里的未知采样点。

需要把报告绑定到实际文件并在交付后复算时，使用可选的[gain-record / gain-review回执流程](GAIN-RECEIPTS.md)。原`gain-check`输出与退出码保持；已有普通报告没有输入身份，不能事后自动升级为可信的原始回执。

需要逐行审阅频段内所有采样点时，13轮提供独立[gain-csv导出](GAIN-CSV.md)，保留原始索引、GT状态和逐点/整段判定；本命令的汇总JSON保持不变。

## MoonBit接口与结果

```moonbit
let points = net.transducer_gain_impedance(
  @rf.complex(100.0, im=20.0),
  @rf.complex(25.0, im=-10.0),
)
let report = @rf.check_transducer_gain(
  points, 1.0e9, 2.0e9,
  minimum_db=4.0, maximum_db=7.0,
)
println(report.to_json().stringify())
```

也可传入`net.transducer_gain(...)`的Γ结果。传入迹线最多100000点，频率须有限、非负、严格递增；空迹线可输入并返回inconclusive。函数校验既有GT状态与可选字段形状，按提供的gain_db判定，不重算gain和dB间的数值关系。旧GT接口的终端域与数值限制继续适用。

report给出闭区间起止、上下限、完整sample_count与state_counts、below_minimum_count/above_maximum_count、range_covered及两个边界采样标志、lowest/highest和reasons。极值保留point、frequency_hz、gain、gain_db、state；并列取最早索引。API索引相对于传入迹线，文件命令使用完整迹线，因此是原文件的零起点频率索引。可选None字段在派生JSON中省略，须结合state解释。

| GT状态 | dB限值与极值处理 |
|---|---|
| finite | 使用有限gain_db |
| underflow / overflow | 正功率仍有有限gain_db，按其检查；不是未知 |
| zero | 精确零功率是负无穷dB；违反任意有限下限，满足任意有限上限；可成为最低点 |
| singular | 未知，计入状态数、不进入数值超限与极值 |

区间和界限均包含等号，无隐式容差；调用方应将允许误差计入限值。只选原始频点，没有插值、外推或连续频带保证。range_covered仅表示数据首尾包住请求区间；start_sampled/end_sampled说明端点是否恰有样本。沿用既有[band-check采样约定](BANDS.md#必须理解的采样语义)：至少一个选中点、范围覆盖、没有奇点且全部满足限值才pass，即使区间内部只有一个采样点也是采样意义的通过。

任何已知超限优先得到fail；否则无样本、范围不足或选中奇点得到inconclusive。reasons可能同时包含below_minimum/above_maximum、incomplete_range、no_samples、singular_samples；通过时为limits_met。失败不能掩盖报告中同时存在的未知或覆盖缺口。有限GT或采样通过均不代表无条件稳定、连续频带或器件认证。

## 验证与范围

新8项测试在JS/Wasm-GC/native各8/8，包含零/上溢/下溢、奇点与失败优先级、边界等号/并列、空/部分频段、单点、非法迹线和100000点边界。纯MoonBit示例在JS/Wasm-GC运行，严格all-target检查与本地模块打包通过。

[独立消费者](../tools/verify-gain-check.py)用Fraction四波方程及Decimal160求合成GT参考，再用声明式掩码、内建极值和人工固定状态表核对报告：39次桥接请求（23个成功报告、16个预期错误）、27份报告比对。6个实际文件CLI进程覆盖0/3/4/2和失败JSON落盘。NXP只新增一组汇总查询，以98个参考样本核对计数和两个极值，不将其算成98次逐点GT数值对照；模型、S矩阵及完整GT输出不随包附送。

原始输入/响应、汇总参考和版本见[独立回执](../evidence/gain-check-20261028/independent-first.json)，命令见[检查记录](../evidence/gain-check-20261028/CHECKS.json)，设计与调查见[DESIGN](../evidence/gain-check-20261028/DESIGN.md)。初期测试的Option断言与参考阻抗数量错误已修正，保留失败记录，未算作旧产品缺陷。05—10数学源码、旧公开签名和旧命令保持；没有重复旧GT/格式/数值全套。

核对了[MoonElec公开接口](https://mooncakes.io/docs/SupremeHuaji/MoonElec)、[circuit-solver公开说明](https://mooncakes.io/docs/hsy-bit/moonbit-circuit-solver@0.1.1)、[scikit-rf频段选点](https://scikit-rf.readthedocs.io/en/latest/api/generated/skrf.network.Network.crop.html)及[Keysight迹线限值流程](https://helpfiles.keysight.com/csg/89600B/Webhelp/Subsystems/gui/content/mnu_utilities_limittests.htm)。限值测试本已有成熟用途；交付差异是MoonBit中两类实际终端GT的采样状态、定位与明确覆盖结论，不主张算法原创、生态唯一或仪器兼容认证。本轮不增加CSV、频变匹配、优化器或新的RF算法。
