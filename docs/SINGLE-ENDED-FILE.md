# 还原单端文档并导出文件

`single-file`把混合模输入还原为实际单端矩阵，输出可继续由文件分析程序读取的规范Touchstone文档，保留原频率、单端端口次序/参考、独立文档参考约定与Information。没有频段选择、插值或新RF变换；复用现有`single_ended_network()`。

## 完整文件接收

```sh
moon build --target js --release --deny-warn
node tools/touchstone.mjs single-file examples/single-file-source.ts '{}' NEW-SINGLE.ts
node tools/touchstone.mjs dump NEW-SINGLE.ts
node tools/touchstone.mjs metrics NEW-SINGLE.ts '{"input":0,"output":2}'
moon run examples/single_file --target js --release
moon run examples/single_file --target wasm-gc --release
```

输入手写四端口数据含非顺序`C3,4 D1,2 D3,4 C1,2`描述符、两频点、不同行对50/75Ω参考和三行Information。输出原单端端口1..4的全部复系数，且不再带Mixed-Mode Order。下游旧指标实际消费该文件的S11反射与S31传输。

原`single`命令仍返回确定性Network JSON；`normalize`仍保留原文件的混合模基底，`legacy`仍拒绝无法保留的Information。已有公开API可以组合成单端文档，本轮不是数学修复或API能力缺失声明；新价值是直接的完整文件互操作出口。

```moonbit
// 此示例输入为无噪声混合模文档；实际噪声不能随意丢弃。
let source = @rf.parse(text)
let single = @rf.document(
  source.single_ended_network(),
  noise_reference_ohms=source.noise_reference_ohms(),
  information=source.information_lines(),
)
let output = single.write()
```

[同类工具的gmm2se](https://scikit-rf.readthedocs.io/en/latest/api/generated/skrf.network.Network.gmm2se.html)及[实际混合模端口次序示例](https://scikit-rf.readthedocs.io/en/latest/examples/mixedmodeanalysis/Mixed%20Mode%20Basics.html)展示这一转换需求。不同软件的模式排列可能不同，本命令使用输入实际描述符，不能只删除模式头或假设所有端口50Ω。这些参考和自编接收例程不构成本项目外部采用证明。

## 条件与错误

- CLI只接受可选`ports`，不需要再次声明配对；非法或未知选项（包括夹具路径、参数转换、drop_noise）拒绝，不读取第三文件。
- 混合模S/Y/Z使用原已有变换，保留原参数及物理单位；先还原系数和单端参考，再移除模式描述符。原单端端口数量/编号及所有频点保持。
- 已经单端的输入直接用原Document writer规范写出，包括保留其已有噪声记录；没有基底变化，也没有新噪声运算。
- 混合模同时有实际噪声记录时，新出口明确报错，因为当前模型未实现该噪声变换。旧解析/规范化与显式确定性`single` JSON视图不改变。
- 输出沿用2.1/Hz/RI/full，并非原排版、注释、版本/格式逐字保留。Information原行保留，源注释不被冒充成校准或器件认证。
- 成功退出0并打印/独占保存Touchstone；输入/配置/不支持组合/IO错误退出2，无新部分输出。已有输出、输入同路径和缺失父目录都明确失败，源字节不变。

没有新公共库API/类型、功率波/校准模型、参考定义或格式；R08频段导出及其全部边界保持。无native执行、实测精度、性能或普适浮点定理声明。

## 独立接收证据

实现前固定完整原始模态文件和全部输出预期。对所选相等实参考端口对，[IBIS2.1附录A](https://www.ibis.org/touchstone_ver2.1/touchstone_ver2_1.pdf)第31页的归一化波矩阵可写为`U=B/sqrt(2)`；独立Fraction计算`Sse=Bᵀ Smm B/2`的32个复系数，没有调用产品求逆求预期。下游指标另由这些原始分数算hypot/log10/VSWR。

`tools/verify-single-file.py --evidence FRESH_PATH`消费两个后端公开包的完整原始/还原条件、矩阵及实际文件；再有限独立解码规范输出，真实CLI读回和计算旧指标。另验未配对S端口、Y/Z物理单位、已单端/legacy/幂等、单端噪声保留与混合噪声拒绝、旧JSON/规范化黄金字节、未知选项与输出保护。错误与所有原始stdout/stderr保留，不只核manifest或自产passed标志。

必要CI门为`Consume restored single-ended document files`，详见[CI-PLAN](../CI-PLAN.md)。旧科学核心未改，本地不重跑其旧生成器/套件；最终head必要CI仍执行全部旧门。
