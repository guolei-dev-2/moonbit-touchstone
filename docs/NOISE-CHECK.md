# 源条件下的 NF 采样上限判定

`Document::check_noise_figure`与`noise-check`把已有源相关噪声系数计算接到Hz闭频段和一个最高dB限值。输出完整源条件、独立噪声参考、原频点索引、逐点NF/超限状态、最差原点和覆盖情况，供文件分析脚本读取。

这是已有NF数组到采样判定的完整工作流。原Γ、物理Ω NF计算及其协方差/插值规则已经存在，本轮不修复它们，也不新增噪声、校准、测量不确定度或文件格式模型。[Keysight N8201A NF指南](https://www.keysight.com/lu/en/assets/9018-01674/user-manuals/9018-01674.pdf)第154页说明频率迹线的NF限值测试；[scikit-rf nf](https://scikit-rf.readthedocs.io/en/latest/api/generated/skrf.network.Network.nf.html)说明源阻抗条件。这些参考及自编例程不构成本项目外部采用证明。

## 实际文件与公开包

```sh
moon build --target js --release --deny-warn
node tools/touchstone.mjs noise-check examples/noise-limits.ts @examples/noise-limit-query.json NEW-REPORT.json
node tools/touchstone.mjs noise examples/noise-limits.ts '{"source_mode":"impedance","source_ohms":[100,0]}'
node tools/touchstone.mjs noise-check examples/noise-limits.ts '{"start_hz":2000000,"end_hz":4000000,"maximum_db":4,"source_mode":"impedance","source_ohms":[100,0]}'
moon run examples/noise_check --target js --release
moon run examples/noise_check --target wasm-gc --release
```

第一条文件判定命令**预期退出3**，同时独占写出有效的fail报告：2..4MHz的两个原点NF约1.760913/3.010300dB，后者超过2dB。第三条把限值设4dB，预期exit0。输出路径已存在、同输入路径或父目录不存在均exit2，保留原输入和已有输出；错误无新部分输出。

```moonbit
let report = doc.check_noise_figure(
  2.0e6, 4.0e6, @rf.complex(100.0),
  maximum_db=2.0, impedance=true,
)
println(report.to_json().stringify())
```

公开包例程实际输出原完整输入、原矩阵/噪声/信息条件，以及Γ和Ω两种完整报告。`maximum_db`必填且有限；显式0和负值均有效。频段有限非负且start≤end。

## 源条件与采样语义

- 默认`source_mode:"gamma"`，未给`source`时为匹配Γ=[0,0]；Γ相对于`noise_reference_ohms`，不是网络端口参考。须有限且在被动源开单位圆内。
- `source_mode:"impedance"`必须给`source_ohms:[R,X]`，Re(Zs)>0且分量有限。直接调用已有物理Ω算法，保留原细小正电阻等语义；不先舍入成Γ。
- CLI仅接受command/ports/start_hz/end_hz/maximum_db/source_mode及所选模式的源键，另一模式源键、配对/夹具等未知项拒绝，不读第三文件。
- 新报告要求单端二端口且存在实际噪声记录。无记录不视作零NF；显式全零协方差记录仍可得0dB。混合模新报告拒绝，旧合法解析/规范化/noise入口不改。
- **先在完整原网络网格上执行已有NF，再筛报告原点**。单噪声记录沿旧规则为常量，多噪声记录不外推；原网格中即便某个错误点在报告频段外也仍报错。不可实现协方差、非法源或最终线性因子错误不降级为pass/inconclusive。
- 闭频段内保留原索引/Hz，严格用NF>maximum_db判超限，没有新增epsilon。`highest`是最大NF的最早原点；无样本为null。
- 任一点超限则fail，优先于覆盖不足；没有超限时，无样本或原网络频率范围不覆盖请求两端则inconclusive，否则pass。`range_covered`仅表示频率范围覆盖，`start_sampled/end_sampled`另标请求端点是否正好是原点。稀疏点之间不作合格承诺。

报告的`kind`为`noise_figure_band_report`、`scope`为`sampled_points_only`、单位dB；含完整源模式/复值/单位、网络与噪声两个参考、原噪声条数、请求/可用频段、覆盖与端点标志、样本/失败数、highest及所有samples。逐点含point/frequency_hz/figure_db/above_maximum/status。它是分析结果，不是字节绑定回执或校准证明。

CLI：pass=0，fail=3，inconclusive=4，输入/物理/IO错误=2。标准输出或新JSON文件都保留同一完整报告；存在fail报告不代表命令发生输入错误。

## 独立接收

实现前手写并冻结四个网络频点、完整矩阵、75/100Ω网络参考、50Ω噪声参考及两条噪声记录。Fmin=1、Γopt=0，协方差与Rn成比例；原1/5MHz记录的Rn25/125Ω在线性插值下给出25/50/100/125Ω。100Ω源相对50Ω为Γ=1/3，因此独立公式F=1+Rn/100给出精确5/4、3/2、2、9/4，再独立取10log10。没有用产品输出/逆变换产生真值。

`tools/verify-noise-check.py --evidence FRESH_PATH`完整消费双后端实际输出、原矩阵/条件与所有报告字段，再运行真实文件CLI、保存并读回JSON，核pass/fail/inconclusive、覆盖/边界/首个并列点、零/负限值、常量与显式零噪声、新旧错误及独占IO。原noise Γ/Ω与normalize完整字节控制另列，只证明兼容，不冒充新科学真值。

必要CI门`Consume sampled source-dependent noise figure acceptance`执行两个公开包后端及真实文件接收。旧科学代码未改，本地只执行新5组测试、相关构建/接口/格式及新接收；完整旧门继续在最终head必要CI运行。数字字段比较、断言数、实际CLI进程及文档CLI分别记录。
