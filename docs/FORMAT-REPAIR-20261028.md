# 2026-10-28 旧格式归一化与角度周期修复

07轮修复两类已复现问题，保留05/06轮数值、端接与噪声修复；公共API不变。

## 归一化不先生成不可表示的系数

旧版Touchstone Y/Z/H/G使用按端口参考阻抗归一化的数据。例如单端口Y的物理值为文件值除以R，Z反向写出也需要除以R。原实现先生成系数或倒数，R=最小正subnormal时会得到无穷，误拒绝最终本来有限的结果：`Yfile=R=5e-324`应得到1S，`Zphysical=R=5e-324`应写成归一化的1。

现在按二进制指数与有界尾数对实部、虚部分别缩放，不先形成超出double范围的系数。Y/Z/H/G的行列物理约定不变，最终结果确实溢出时仍拒绝。独立Fraction参考使用可精确开方的二次幂参考阻抗，覆盖正常、极大、极小及逐端口不同参考；写出预期直接从独立构造的2.1物理矩阵计算，不只检查自身往返。

## 先在度数中处理周期

Touchstone角度以度为单位。原实现将巨大有限度数先换成弧度，舍入后丢失周期；`3.6e21`是精确可表示的360整数倍，旧结果却不是实轴方向。现在先对360取余，再转弧度。MA、DB及噪声Γopt共用这一处理。独立预期用输入binary64的精确Fraction求余，随后只对小角度求三角函数。

## 本轮证据与范围

新增三个解析/写出边界测试先失败，修复后通过。相关测试为新增3项、legacy3项、document4项；JS、Wasm-GC、native各10/10。`moon fmt`、`moon info`、all-target严格检查与JS release构建通过。公共mbti与05/06数值/RF核心源码身份保持。

70次实际桥接请求包括30次独立归一化输入/输出、32次MA/DB周期、2次最终溢出拒绝、3次噪声与信息保留、2次非均匀网格群时延及1次零传输拒绝。群时延保持既有端点单边/内部跨邻点割线定义；没有改成另一种不均匀网格插值导数。标准要求噪声频点数大于零、信息段位于网络数据之前，原实现正确，未修改这两项。

```sh
moon test format_extreme_test.mbt --target js --deny-warn
moon test legacy_test.mbt --target js --deny-warn
moon test document_test.mbt --target js --deny-warn
moon build --target js --release
python tools/verify-format-extreme.py --evidence format-new.json
```

原始请求与响应见[独立回执](../evidence/format-repair-20261028/independent-first.json)，三个后端的相关测试见[检查记录](../evidence/format-repair-20261028/CHECKS.json)。05/06通过集合与厂商输入未重跑，本轮70次不能替代历史回执。标准依据为[IBIS Touchstone 2.1](https://www.ibis.org/touchstone_ver2.1/touchstone_ver2_1.pdf)的角度、旧格式归一化、噪声计数和信息段位置规则；未附送标准全文或新增厂商数据。
