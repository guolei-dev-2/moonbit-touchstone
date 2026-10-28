# 两份原始S文件的严格对照

`s-compare`让测量/修订文件的接收方直接检查两份原始S数据之间的复数差，记录双方实际输入字节身份、可比条件、限值判定与原坐标见证。旧`band-check`检查单个网络的绝对量；`gain-review`只复现同源回执，仍在SHA256或字节数不符时返回`input_mismatch`。复数减法和模长复用既有运算，不主张新数学。

```sh
moon build --target js --release --deny-warn
node tools/touchstone.mjs s-compare examples/s-compare-baseline.ts '@examples/s-compare-query.json' NEW-COMPARISON.json
```

此例故意退出3并正常保存报告：在1MHz的S21中，baseline的+1/2变成candidate的−1/2，两者幅度/插损相同，但`candidate-baseline=-1`，复数差模为1。2MHz的S12另有`3/16+4/16 i`差，模为5/16。限值0.5时，8个元素全部计入、仅1个超限；限值1包含等号，全部满足。S量和限值都无量纲。

## 输入与对应声明

第一个文件是baseline；`candidate_file`指定第二份原始文件。`maximum_absolute_s_delta`必填，须有限且非负，没有默认容差或隐藏epsilon。`physical_alignment_declared:true`表示调用方声明：同一数值索引对应相同物理端口、参考平面及本次对照所需的测量条件。报告固定记录`caller_declared_unverified`和`physical_certification:false`，文件和哈希不能核实该声明。省略或false时不给数值通过结论，报告`physical_alignment_not_declared`；错误类型则报配置错误。

```json
{"candidate_file":"examples/s-compare-candidate.ts","maximum_absolute_s_delta":0.5,"physical_alignment_declared":true}
```

两文件各自沿用ASCII/64MB及现有网络预算。选项可为`@文件`，沿用ASCII/1MB预算；路径相对当前工作目录。1.x的`.sNp`按文件名推端口数，也可分别显式给`ports/candidate_ports`。未知键拒绝，夹具路径键不会作为额外输入读取；调用方不能覆盖内部输入身份。

仅比较两份已经是**原始single-ended S**的数据。使用`Document::raw_network`，先检查以下条件：

- 无混合模描述符；非S或mixed-mode为不兼容，不转换或恢复模式。
- 端口数N相同，行列都使用原有零起点S[output,input]。
- 频点个数、每个原始索引的parsed-Hz数值完全相同。文件单位可不同，只要解析后的Hz一致。
- 有序正实参考阻抗向量完全相同。不同顺序、相邻Double差值也不自动对齐。

不排序、重排、裁剪、补点、插值、重归一化或对齐参考平面。有效但不兼容的输入返回明确原因，如`port_count`、`frequency_count`、`frequency_grid`、`reference_ohms`、`non_S_representation`、`mixed_mode`；`comparison`为null，没有部分数值通过。无效文件仍按现有解析错误处理。

## 报告与见证

JSON的`kind`为`s_comparison_report`，`scope`为`deterministic_S_only`。`sources.baseline/candidate`分别记录实际消费payload的SHA256/字节数、参数、端口数、频点数/首尾Hz、参考阻抗、模态描述符和噪声存在/记录数。Node每个角色只打开读取一次，对同一份验证过的ASCII字符串做指纹并传给MoonBit；不另开文件取哈希。注释、信息和LF/CRLF均参与身份。

`conditions`明确数值配对规则、caller声明、限值、包含等号及`delta_definition:candidate_minus_baseline`。兼容时：

- `evaluated_elements/exceeded_elements`覆盖全部原始点的N²个元素。
- `maximum`是全局复差模最大见证；`per_sij`按行优先给N²个通道，每项有完整计数与最大见证。
- 每个见证给出`point/frequency_hz/output/input`、双方复数operand、带符号`delta`和`absolute_s_delta`。不只比较幅度或dB。
- 并列时取最早原点；全局并列按(point,output,input)先后。明细最多N²项，计数和判定没有截断采样。

可比较已有噪声记录的S文档，但每源明确`noise_not_compared:true`和噪声存在/条数。即使S差为0，也不声称整个含噪网络相等；不比较噪声参数、统计不确定度或元数据的物理含义。信息/换行变化通过双方原字节身份体现，可以在相同S下通过0限值；旧gain-review对这种改字节仍拒绝复现。

有限operand若产生不可表示的delta分量或模长，整个操作明确报错；没有NaN JSON、静默丢点或伪造有限报告。直接复用既有`Complex.sub/magnitude`，不承诺全Double域理论或未测最大规模吞吐。

| 退出码 | 结果 |
|---|---|
| 0 | `within`：全部复差模≤调用方限值 |
| 3 | `exceeds`：至少一个超限，完整计数和见证仍输出 |
| 4 | `incompatible`：条件或对应声明不足，comparison为null |
| 2 | 配置、解析、IO或不可表示运算错误；没有部分报告 |

省略输出路径时报告写stdout；指定路径时独占创建、stdout为空。已有路径、输出与任一输入同路径、父目录不存在均按原IO规则报错，保留输入/已有输出。报告先完整生成再写出；错误写stderr，不把失败当成通过报告。

## 验收与职责

新[独立文件消费者](../tools/verify-s-compare.py)使用预先手写的两频两端口分数真值，核对8元素计数、两个非零delta与符号、全局/每Sij原坐标、0/.5/1限值、反向角色、零/并列、双源身份及实际open次数。另覆盖N/grid/reference/参数/模态/声明不兼容，噪声排除、旧回执改字节拒绝、坏配置/文件/预算、不可表示减法/模长和独占输出保护。生成夹具不是测量数据，旧单输入结果不充当复差数值oracle。

核心比较与序列化在私有MoonBit桥接helper；Node只处理文件、参数、指纹和退出码。公共库API、旧单输入命令、RF数学及回执协议保持。此文件接收方仅在JS桥接实际运行；all-target严格检查不等于在Wasm/native运行新命令。没有新Touchstone格式、网络差分DUT导出、校准、参考波或来源认证模型。

同类工作流背景见scikit-rf官方[Network算术操作](https://scikit-rf.readthedocs.io/en/latest/tutorials/Networks.html#arithmetic-operations)：复S差与匹配频率是常见分析用途；本命令不采用其可选重采样路径。不主张算法原创或生态唯一。
