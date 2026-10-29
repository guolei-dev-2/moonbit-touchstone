# 有限复分量的 DB 读写修复

修复既有 Touchstone DB 读写的同一处尺度缺陷：径向模长可能超出 binary64，而实部、虚部及 DB 数字仍可表示。公共 API、文件版本、参数单位、CLI 命令与普通数据输出保持。

## 反例与定义

[IBIS Touchstone 2.1](https://www.ibis.org/touchstone_ver2.1/touchstone_ver2_1.pdf)第6页定义 DB 为 `20 log10(|z|)`，相位单位为度；第29页兼容说明允许当前版本的 S/Y/Z/H/G 使用 DB。模长和笛卡尔分量是不同的可表示性条件。

手写 `6168 45` 对应的两个分量都是 `10^(6168/20)/sqrt(2)`，约 `1.7761719292909023e308`，仍小于 binary64 最大值。原 reader 先计算模长约 `2.5118864e308`，中间溢出后误报 `invalid magnitude`。原 writer 对有限的 `1.6e308+j1.6e308` 先求模长，也误报 `non-finite formatted value`；其 DB 应约为 `6167.092699609758`，角度为45度。

这些是合成的有限输入边界，不表示实际器件具有这些数值或测量性能。

## 实际使用

先用项目指定的工具链构建，再使用新输出路径：

```sh
moon build --target js --release --deny-warn
node tools/touchstone.mjs normalize examples/db-finite-components.s1p '{}' db-finite-ri.ts
node tools/touchstone.mjs dump db-finite-ri.ts
node tools/touchstone.mjs legacy db-finite-ri.ts '{"format":"DB"}' db-finite-back.s1p
```

第一步把原 DB 文件读入并写成标准2.1/Hz/RI；最后一步通过现有 legacy writer 输出 DB。已有输出不会被覆盖。`parse_legacy`、`parse` 和 `Network::write_legacy(format="DB")` 的签名不变。

```sh
moon run examples/db_cartesian --target js --release
moon run examples/db_cartesian --target wasm-gc --release
```

公开包例程实际读取带75Ω参考和信息行的2.1物理Z文件，输出完整矩阵及规范RI文件；另构造逐端口参考不同的二端口S，实际输出两频点、全部四个S元素的DB文件。物理Z仍为Ω，版本2.1的参考阻抗不参与旧版归一化。示例是本项目编写的接收者，不是外部采用证明。

## 处理与保留的边界

仅在原径向计算溢出时启用补充路径。reader 利用 `6160 dB = 20 log10(10^308)`，先计算减去该基准后的有限尺度、投影到两个分量，再恢复 `1e308`。writer 把有限分量除以其最大绝对分量，再分开计算尺度与归一化平方和的对数。普通有限模长仍走旧路径，巨大角度仍先在度数中取周期。

- `6168 0` 等真正超出分量范围的输入仍拒绝，保留 `invalid magnitude` 错误；NaN/Infinity 数字仍拒绝。
- MA 仍需要有限的径向模长；DB 的有限数字不能精确表示零，因此零值 DB 写出仍拒绝。原有极小 DB 下溢为零的行为保持。
- RI、频率单位与顺序、二端口21_12序列、每端口参考、旧版Y/Z/H/G归一化及文档信息/噪声/模态处理不变。
- 不承诺 DB 超越函数的逐位往返、所有舍入切点，或利用后续归一化挽救已经不可表示的原始笛卡尔分量。没有改 RF 数学、校准模型、噪声模型或文件格式。

## 独立验收

`db_cartesian_test.mbt` 在改实现前有三项因上述产品缺陷失败，错误记录保留于本轮报告。独立预期先用90位 Decimal 冻结，使用精确45度分量关系与原始复系数的平方和对数；自身往返不是唯一真值。

`tools/verify-db-cartesian.py --evidence FRESH_PATH` 消费 JS/Wasm-GC 例程的完整输出，独立核 DB/角度字段、全部矩阵坐标、Hz网格、参考与信息行，再让真实文件 CLI 读回。它还新建任意文件，核2.0/2.1、旧Z归一化、普通黄金输出、巨大角度周期、真正溢出、MA/零DB错误与独占输出保护。输出目录和回执必须为新路径，失败样本不覆盖。

CI 的 `Consume finite Cartesian DB input and output` 实际运行两个后端例程及该文件接收者。all-target检查不代表 native 运行；本轮不把历史科学生成器或旧回执算作新执行结果。
