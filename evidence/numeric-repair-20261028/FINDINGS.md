# 实证缺陷与修复

F1（已修）：Complex::divide中间溢出。有限(1e308+i1e308)/(1+i)被拒绝；before-numeric-js.log保存Failure(non-finite complex result)。独立解析值为1e308+0i；Fraction按原binary64精确输入确认更多极值案例。采用二进制指数归一化和末端scalbn，纯实/虚分母逐分量除以保留不同尺度分量。不可表示最终商继续拒绝。

F2（已修）：invert_matrix用hypot作行尺度/主元评分，有限1.3e308+i1.3e308的模长溢出产生inf/inf，错误判奇异。实际逆约3.846153846153847e-309−i3.846153846153847e-309。before-numeric-js.log保存拒绝；现改为有限分量最大范数，并由实际Z→Y消费验证。

F3（已修）：1e308*[[1,1],[-1,1]]消元产生2e308，而有限逆为5e-309*[[1,-1],[1,1]]。before-equilibration-repro-js.log保存Failure。增加行尺度平衡，在归一化系统求逆，最后按原行尺度恢复列；不提前形成tiny-scale倒数。安全主元门槛1e-12保留，三种尺度近奇点继续拒绝。

初始before-numeric-js三测试2失败1通过；修正后独立Fraction覆盖35有限商、7溢出商、5复矩阵逆。本轮最终JS/Wasm-GC各38/38，native新数值5/5与Fraction2/2，均新执行。严格all检查、release构建、两个rf_03消费者、最终格式检查通过；接口生成与before完全一致。

tools/verify-repair05.py通过19次定向请求：独立scikit-rf微波网络与解析限值案例，覆盖非顺序配对/参考、级联/两侧去嵌入、不可逆夹具、NaN/Inf、inclusive限值/截断/覆盖不足/空区间/有源VSWR/零传输波动。数值比较最大绝对差3.337167946540778e-16（本组S参数与参考值，非全域保证）。无新厂商下载，无历史368/1103或55全套重跑。

保留的开发失败不是产品缺陷：before-equilibration-js.log最初因测试字面量5e-309缺小数点而编译失败，修正为5.0e-309后取得真实运行失败；targeted-rf-first.json中的首个级联拒绝源于scikit-rf把一维双元素z0解释成频率方向，参考构造改为明确f×port二维。另纠正桥接cascade/deembed只有text的消费方式。最终独立回执targeted-rf-after.json全部通过，未裁换原RF输入目标。

无须变更的RF端口/阻抗与采样三态在定向检查中符合现有契约；噪声及大端口旧证据按原源身份保留，不能把旧回执哈希写成当前算法哈希。所有before/after身份另存，不改旧记录。
