# GT逐点CSV审阅

`gain-check`汇总计数和极值；审阅频段内每个采样点时，13轮提供独立`gain-csv`与纯MoonBit `transducer_gain_samples_csv`。它复用既有Γ/Ω GT和采样规则，导出所有选中原始点，保留零功率、奇点及正功率上/下溢的区别。旧数值、汇总JSON和回执协议保持。

## 文件与库用法

```sh
moon build --target js --release --deny-warn
node tools/touchstone.mjs gain-csv examples/power-gain.s2p '@examples/gain-check-ohms.json' NEW-GAIN.csv
moon run examples/gain_csv --target js
moon run examples/gain_csv --target wasm-gc
```

文件命令与[gain-check](GAIN-CHECK.md)选项相同：`start_hz/end_hz`、至少一个有限`minimum_db/maximum_db`，可选`terminal_mode:"gamma"`及默认零Γ源/负载，或显式`"impedance"`与必填`source_ohms/load_ohms`。两类单位键不能混用。示例采用100+j20Ω源、25−j10Ω负载、1–2GHz、4–7dB限值，第一点pass、第二点fail，整段fail；正常保存CSV后退出3。

第四个参数可省略，CSV将输出到标准输出；已有输出文件拒绝覆盖。退出码0/3/4分别表示整段采样pass/fail/inconclusive，2表示配置、解析、域或IO错误。空表不等于pass，自动化脚本需处理3/4的正常分析结果。

```moonbit
let csv = @rf.transducer_gain_samples_csv(
  net.transducer_gain_impedance(
    @rf.complex(100.0, im=20.0),
    @rf.complex(25.0, im=-10.0),
  ),
  1.0e9, 2.0e9, minimum_db=4.0, maximum_db=7.0,
)
println(csv)
```

公共接口见[pkg.generated.mbti](../pkg.generated.mbti)，可执行库消费者见[examples/gain_csv](../examples/gain_csv/main.mbt)。函数返回String，错误通过raise；只渲染规范GT迹线，不重算其gain与dB之间的关系。复用旧报告函数校验整条迹线和限值，因此选区外的非法点也会拒绝。沿用最多100000点、有限非负且严格递增频率、五种规范状态及字段形状，允许空迹线。

## 固定列与空值

CSV为ASCII、逗号分隔、LF换行、无BOM；首行为以下14列，之后每个选中采样点一行，不截断、不只保留错误点：

```text
point,frequency_hz,gain,gain_db,state,start_hz,end_hz,minimum_db,maximum_db,below_minimum,above_maximum,sample_status,report_status,range_covered
```

| 列 | 含义 |
|---|---|
| point / frequency_hz | 完整输入迹线的零起点索引和Hz；闭区间选点后保留原索引与顺序 |
| gain / gain_db / state | 线性GT、dB和规范五态；缺少的可选值为空单元格，即空字符串，不写null/NaN/伪造0 |
| start_hz / end_hz | 本次闭区间Hz边界，每行重复 |
| minimum_db / maximum_db | 有限dB界限，未给的界限为空，显式0保留 |
| below_minimum / above_maximum | 已知点为true/false，无相应界限为false；奇点为空，表示未知而非通过 |
| sample_status | 单点pass/fail/unknown，只说明该点的限值结果 |
| report_status / range_covered | 整段采样pass/fail/inconclusive及首尾范围是否覆盖，每行重复 |

有限边界包含等号，无隐式容差。`zero`的gain为0、dB为空，物理含义为负无穷dB，违反任意有限下限并满足有限上限；`singular`的gain/dB和两个标志均为空，sample_status为unknown。正功率`underflow`可有gain0、`overflow`可缺gain，但有限dB仍参与正常限值判定。读取空单元格必须同时读取state，不能把零功率当奇点，或把所有空值填0。

单点pass可与整段fail或inconclusive并存；未覆盖频段、无选中点和奇点的全局优先级沿用[gain-check](GAIN-CHECK.md)。无选中点或空迹线只输出表头，CLI退出4。没有插值、外推、连续频段保证或器件认证。核心Double格式可能使用科学记数法；数字写法不是固定小数位协议。

本表不携带Γ/Ω终端条件、参考阻抗、文件身份或签名。需要这些上下文时，请同时保留使用相同选项生成的[gain-record回执](GAIN-RECEIPTS.md)；CSV不能替代回执。既有v1回执仍只重放gain-check。本功能不修改输入Touchstone、不读取CSV、不生成XLSX，也没有实际操作Excel或作兼容认证。

## 验证与来源

新7项公共渲染器测试在JS/Wasm-GC/native各7/7，采用固定五态表、边界/原始索引、空表、覆盖、非法选区外点和100000/100001容量。新纯MoonBit例程在JS/Wasm-GC运行，严格all-target、格式和API生成检查通过。

[独立消费者](../tools/verify-gain-csv.py)用Python标准库csv.DictReader和固定真值核对27个实际CLI进程、29项消费者检查，包括Γ/Ω、五态、空表、原始索引、失败CSV保存/拒绝覆盖、非法配置及10万行逐点读取。两个普通gain-check控制与封存12轮payload相等，一个旧失败回执完整复核结果保持，v1不接受新增gain-csv命令。两次纯MoonBit示例输出读取计入29项，未重复运行。

旧数值/回执全套、RF参考环境和厂家模型集合没有重跑，没有新增厂家输入或GT数值对照。实际命令与原始结果见[独立回执](../evidence/gain-csv-20261028/independent-first.json)、[检查](../evidence/gain-csv-20261028/CHECKS.json)及[示例CSV](../evidence/gain-csv-20261028/ohm-fail.csv)。初期新例程误用了未定义的print，已改为既有println并保留诊断；不记作旧产品缺陷。

调查了[MoonFrame0.5.5](https://mooncakes.io/docs/ihb2032/MoonFrame@0.5.5)的CSV渲染、[moonlake0.5.0](https://mooncakes.io/docs/superbigcup325/moonlake@0.5.0)的CSV/Parquet查询、[scikit-rf表格导出](https://scikit-rf.readthedocs.io/en/latest/_modules/skrf/io/general.html)和[Keysight迹线导出](https://helpfiles.keysight.com/csg/e5072a/measurement/data_output/saving_trace_data_to_a_file.htm)。差异是MoonBit里实际终端GT的选点、状态与限值审阅列，不主张CSV创新、生态唯一或已验证的第三方集成。无新增运行依赖或复制上游代码。
