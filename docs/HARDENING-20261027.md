# 2026-10-27 上限端口与无源性边界加固

本轮从冻结 0.3.0 源码出发，未重写已有算子。增加一个32端口解析幂波不变量回归，以及 `tools/verify-boundaries.py` 独立验证器；公共 API 和数学实现不变。修正 SOURCES 中“无第三方下载样本”的过时表述，并在 THIRD-PARTY 补上 NXP 的许可边界。

## 新验证范围

- 无源性30例：1/2/16/31/32端口；复数左右酉旋转、精确无损/秩亏、最大特征值在容差带两侧，以及每列功率小于1但相干组合有增益的反例。独立 oracle 是 `numpy.linalg.eigvalsh(I-SᴴS)`，不复写 MoonBit 的 Cholesky 实现。
- 混合模9组：31端口15对、32端口16对、32端口1对，各测试S/Y/Z；随机非顺序配对、对内相等且跨对不同的参考阻抗、保留单端端口、正向矩阵/有效参考与反向恢复。正向对照 scikit-rf `renumber` + `se2gmm`，反向对照原始独立网络。
- 错误路径7例：同端配对、重叠配对、越界端口、对内不等参考阻抗，以及零/负/超范围诊断容差。

实际执行55次桥接请求全部通过。混合模正向最大绝对差为1.1368878926877637e-13，反向为1.7708057242771247e-14；这些是本组 S/Y/Z 合成输入的观察值，不是所有表示、单位与输入的统一精度保证。逐组结果、原始IPC、版本与源码SHA256见[运行回执](../evidence/hardening-20261027/reference.json)，[检查记录](../evidence/hardening-20261027/CHECKS.json)及同目录原始日志。

固定 moonc 0.10.14+7d59c7ec9 / moon 0.1.20260920，Node24.11.0；Python3.14.4、NumPy2.5.3、scikit-rf2.1.0。`moon check --target all --deny-warn` 通过，JS与Wasm-GC各31项通过，JS release构建通过；`moon info` 生成接口与冻结版逐字一致。

## 数学边界

`diagnostics(tolerance=...)` 对正实参考功率波的无量纲 Hermitian 形式使用两个严格正定 Cholesky 检查。若最小特征值大于tol，返回passive；在−tol与tol之间的带返回boundary，含理想无损网络；低于负侧门限返回active。源码的严格判断将精确−tol归于active，精确+tol归于boundary；浮点切点附近不构成认证保证。boundary也可能含轻微有源量，不能把它自动当作严格无源PASS。

Cholesky不是奇异值分解，不产生奇异值，也不能把未移位的严格正定检查直接当成半正定检查。参考：[NumPy Cholesky](https://numpy.org/doc/stable/reference/generated/numpy.linalg.cholesky.html)、[Hermitian eigenvalues](https://numpy.org/doc/stable/reference/generated/numpy.linalg.eigvalsh.html)。混合模定义依据[IBIS2.1附录A](https://www.ibis.org/touchstone_ver2.1/touchstone_ver2_1.pdf)。

## 复现

```sh
moon build --target js --release --deny-warn
python -m pip install -r tools/requirements.txt
python tools/verify-boundaries.py --evidence boundary-new.json
moon test --target js --deny-warn
moon test --target wasm-gc --deny-warn
```

回执路径必须尚不存在，避免覆盖既有结果。Python只参与开发验证，库/CLI运行不依赖它。本轮未重跑旧368/1103集合及NXP/Johanson样本；其有效历史结果保留原日期。没有推送、发布、改报名表或取得正式验收。
