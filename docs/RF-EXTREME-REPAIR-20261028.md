# 2026-10-28 稳定性、复负载与小噪声修复

本轮继续修复0.3.0已承诺功能，保留05轮的复数/矩阵尺度修复。公共API和原有格式范围不变。

## 有限MAG与极大K

旧MAG计算分母包含K²，极大但有限的K会让它溢出，进而把有限增益错误算成0；K本身超出double时还会误报不稳定。现在用等价的耗散裕量形式比较稳定性、计算MAG，不先形成K²。接近单位反射时，K的分子也改用等价因式展开，避免相减丢掉小的正裕量。K无法有限表示时仍为空，不伪造K值，有限MAG可独立返回。

匹配二端口S11=S22=0且|S12S21|<1时，MAG严格等于|S21|²。例如S21=2、S12=1e-200，结果是4而不是0。新回归还覆盖最小subnormal反向传输、接近单位反射以及正常/潜在不稳定器件。

## 齐次复阻抗端接

对阻抗负载以N=ZL−Z0、D=ZL+Z0表示条件D·a=N·b，在相加前按二的幂缩放。求解(D−N·Stt)·a=N·Str后恢复剩余端口，不需要先计算可能发散的Γ=N/D。

这修复两种合法输入：ZL=Z0=1e308ohm仍是Γ=0的匹配负载；ZL=−Z0虽是Γ表示的极点，但在Stt可逆时整个端接系统仍可解。后一种单端接结果为Srr−Srt·Stt⁻¹·Str，不能因单独Γ不可表示就拒绝。真正的反馈奇点仍拒绝，例如S22=1/2、ZL=−3Z0。二进制缩放还保留这类精确抵消，避免任意除法人为制造小的非零主元。

独立Fraction真值覆盖极大/极小参考、复负载、有源负载、Γ极点和逆序多端接端口；剩余端口的顺序和原参考保留。没有新增负阻抗稳定性认证，仍是已有的逐频点线性端接运算。

## 小的非零噪声不等于无噪声

旧反解在Rn和相关矩阵绝对值小于1e-13时直接返回无噪声，错误抹去了合法的小噪声状态，且阈值混用了ohm/siemens等单位。现在只把精确全零矩阵规范化为无噪声；相对PSD检查和非物理状态拒绝保持。相关矩阵除Rn改用复数除法，避免先取巨大倒数。

新增测试与独立消费者覆盖Rn=1e-200、1e-14及正常尺度，参考为1、50、1e6ohm；scikit-rf相关矩阵在按Rn缩放后比较，避免用固定绝对误差把“全零错误结果”也判通过。插值、级联和双侧去嵌入消费均有对应检查；独立中间协方差真值避免仅自身往返。

## 本轮实际证据与复现

JS、Wasm-GC、native各执行相关RF回归8项（新极值3项+已有RF5项），均通过；严格all-target检查、release构建及JS/Wasm-GC示例通过。05轮38项、Fraction尺度集合、历史31/55、368/1103和厂商输入没有重跑，不能换算为本轮全套成绩。

独立消费者共60次桥接请求。MAG参考使用800位Decimal从精确binary64输入计算原始K和K−sqrt(K²−1)表达式；在14个极限点，scikit-rf2.1.0的binary64 max_gain也发生溢出/消减差异，已明确记录，未盲从它或把同一算法复制成oracle。负载用精确Fraction闭式代数，噪声用scikit-rf2.1.0/NumPy2.5.3的独立相关矩阵及插值。

```sh
moon test rf_extreme_test.mbt --target js --deny-warn
moon test rf_test.mbt --target js --deny-warn
moon test rf_extreme_test.mbt --target wasm-gc --deny-warn
moon test rf_test.mbt --target wasm-gc --deny-warn
moon test rf_extreme_test.mbt --target native --deny-warn
moon test rf_test.mbt --target native --deny-warn
moon build --target js --release --deny-warn
python tools/verify-rf-extreme.py --evidence rf-extreme-new.json
```

参考职责及原始响应见[独立回执](../evidence/rf-extreme-repair-20261028/independent-final.json)，实际命令/退出码见[检查记录](../evidence/rf-extreme-repair-20261028/CHECKS.json)。失败复现保留，不将参考夹具最初噪声R值不匹配的问题误算作产品bug。独立参考只用于开发，库不增加Python运行依赖；输入均为项目合成数据，厂商原模型仍不附送。有限回归不构成所有病态输入、全频稳定性或设备认证保证。
