# 深入修复06：失败、依据与闭环

本轮承接05已完成状态；只修改当前amplifier.mbt与noise.mbt，05复数/矩阵修复保留。before-rf-extreme.log保存3个原始失败（3/3失败），另有before-impedance-pole.log保存Gamma极点合法负载的拒绝；不是仅旧测试复跑。

1. MAG中K²溢出将有限增益算0；K无法有限表示时还会误报不稳定，近单位反射的裕量相减也可能丢失。改为等价因式化耗散裕量比较及MAG表达式，K字段仍可为空。800位Decimal直接计算原始K与K−sqrt(K²−1)，19个稳定性输入核对通过；scikit-rf2.1.0 binary64在14个极限点也有溢出/消减差异，原始分歧在独立回执中。
2. ZL=Z0=1e308ohm本应是匹配负载，旧ZL+Z0先溢出而拒绝；改为二进制缩放的齐次负载系数，覆盖极小/subnormal到极大参考。
3. ZL=−Z0虽然使Gamma=N/D单独发散，但完整反馈系统可逆时仍有有限解；原实现错误拒绝。改为直接求解(D−N*Stt)*a=N*Str，支持逆序多端口，不删合法输入。S22=1/2、ZL=−3Z0的真实反馈奇点继续拒绝。中间版本用任意除法缩放制造了1e-16伪主元，after-impedance-pole.log保留该失败；随后用精确二进制缩放修复，最终相关回归通过。
4. noise_point以带单位的1e-13绝对floor将合法非零Rn抹零；现在只把精确全零相关矩阵规范为无噪声，相对PSD检查保持，相关矩阵除Rn不提前取倒数。Rn=1e-200/1e-14及正常值、1/50/1e6ohm参考下，独立scikit-rf噪声插值/协方差核对通过，且检查按Rn缩放而非用宽松绝对容差放过全零错误。

最终独立消费者60请求，涵盖MAG、精确Fraction复负载/多端接、噪声插值/级联/去嵌入。初次independent-first.json失败是参考文本把option-line噪声R固定50而scikit-rf使用1ohm；这是已查证的参考夹具错误，改为明确匹配后保留independent-after.json。后续为完成Gamma极点与多端接承诺而修改产品，按新源码执行independent-final.json，全部通过；未裁掉失败原输入。

最终JS/Wasm-GC/native各执行8个相关RF回归（新极值3+现有RF5），严格all检查、release构建、双后端消费者通过；生成接口与before一致。05未变化的38/Fraction以及31/55、368/1103和原厂下载未重跑。末轮代码更改后只重复受影响检查，保留每阶段记录，不把先前通过冒充最终源码通过。

SOURCE-BEFORE.json与SOURCE-AFTER.json绑定源码；REPAIR.diff保留改动。开始时未及时记录旧编译产物哈希，故在报告目录从不可变05 ZIP逐文件核对后重建旧JS release用于身份对照，没有再运行旧测试；COMPILED-IDENTITY-FINAL.json明确标注before为本次重建，不伪装成开始时观察到的二进制。中间产物身份也保留。

无未完成范围内必须项。结论仅针对当前有限double模型和上述定向依据，不代表所有病态网络精度、设备/全频认证或赛事验收。
