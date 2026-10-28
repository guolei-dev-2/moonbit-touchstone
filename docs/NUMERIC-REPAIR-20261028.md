# 2026-10-28 有限复数与矩阵尺度修复

本次实际修改复数除法和矩阵求逆，保留公共API、输入域、近奇点拒绝门槛及既有射频职责。不是仅更新文档，也没有靠拒绝合法输入绕过失败。

## 已复现并修复

1. `(1e308+i·1e308)/(1+i)` 的结果为有限 `1e308`，旧实现在相加中间项时溢出，错误返回non-finite。现在分别提取操作数的binary64指数、用二的幂归一化，最后恢复商的指数。纯实/纯虚分母直接按分量除，保留巨大分量旁边的小分量。零分母、非有限输入及不可表示结果仍明确失败。
2. 一阶矩阵 `[1.3e308+i·1.3e308]` 有有限逆，旧选主元使用复数模长，模长超出double范围导致inf/inf比较，误报奇异。现在按有限实/虚分量最大值定行尺度。
3. `1e308*[[1,1],[-1,1]]` 的逆为 `5e-309*[[1,-1],[1,1]]`，旧消元仍会形成 `2e308` 并失败。现在先平衡行尺度，在归一化系统上消元，最后按原行尺度恢复逆矩阵的列；不提前形成可能溢出的tiny-scale倒数。原1e-12相对主元安全门槛保留，不增加对奇点的扰动。

## 独立真值与范围

新增 `numeric_scale_test.mbt` 的5个回归测试覆盖上述失败、subnormal、不同分量尺度、非有限/零分母、不同尺度近奇点拒绝和巨大Z→Y的实际网络消费。

`tools/generate-scale-reference.py` 用Python `fractions.Fraction` 对输入binary64值做精确有理数运算，仅在最终期望值转double；2×2逆用精确伴随矩阵/行列式公式，未复制MoonBit的Gauss-Jordan。它生成的 `numeric_scale_reference_test.mbt` 包含35个有限商、7个不可表示商及5个尺度不同的复矩阵逆，分别按相对误差和subnormal绝对误差检查。重现时给生成器全新 `--test`、`--receipt` 输出路径，不覆盖现有回执。

`tools/verify-repair05.py` 对19次桥接请求使用scikit-rf2.1.0/NumPy2.5.3独立对照非顺序混合模、不等内外参考的级联/双夹具去嵌入，并以解析样例检查参考不匹配、不可逆夹具、NaN/Inf拒绝、限值等号、明细截断、覆盖不足时失败优先、空区间、有源VSWR、零传输波动。独立DUT来自scikit-rf，不使用本库先级联再去嵌入当唯一oracle。

scikit-rf构造双频二端口时，一维z0向量存在形状歧义；验证器明确用频点×端口的二维参考数组，输出由scikit-rf独立读取。最初参考构造错误的回执和修正后的结果均保留，不把参考脚本错误冒充产品缺陷。

## 实际验证

固定moonc0.10.14+7d59c7ec9：严格all-target检查通过，JS/Wasm-GC各38/38通过；native新增数值测试5/5与Fraction测试2/2通过，release桥接构建通过。公共接口生成结果保持不变。历史368/1103、55请求和NXP/Johanson样本未重跑，其日期及数值不作为本轮成绩。

```sh
moon check --target all --deny-warn
moon test --target js --deny-warn
moon test --target wasm-gc --deny-warn
moon test numeric_scale_test.mbt --target native --deny-warn
moon test numeric_scale_reference_test.mbt --target native --deny-warn
moon build --target js --release --deny-warn
python tools/verify-repair05.py --evidence repair-new.json
```

这些是有限double范围缺陷和定向回归证据，不保证任意病态系统的条件数、所有浮点舍入切点或超出double范围的中间/最终结果。标准库 `math.scalbn` 与位转换由固定本地API查证，无新增运行依赖。数据全部合成；厂商原始数据继续不随MIT包分发。
