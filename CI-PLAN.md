# 必要持续验证计划

`.github/workflows/ci.yml`是实际执行源。每次push/PR/手动运行在固定SDK和普通Ubuntu runner上执行一个`check` job；最终交付只采信同仓库、精确最终head的真实终态及所有必要步骤。

保持现有格式、严格all-target检查、完整JS/Wasm-GC单测、release JS、公共接口再生成、原Node CLI、全部既有独立科学/文件消费者、双后端例程、模块封包和源码未改写门。新增原频点裁剪门不替换或跳过这些旧门。

## 原频点文件导出的必要接收门

```sh
moon run examples/crop_document --target js --release > _build/ci/crop-example-js.json
moon run examples/crop_document --target wasm-gc --release > _build/ci/crop-example-wasm-gc.json
python tools/verify-crop.py --evidence _build/ci/crop.json
```

实际步骤名：`Consume original-frequency cropped documents from package and files`。

- 原始完整四点物理Z文件与独立整数矩阵先固定。两后端公开包消费裁剪结果、全部源条件和旧指标，不能只核编译或数组长度。
- 文件接收者用原工作字节的实际复制件，执行裁剪、有限独立规范解码、CLI读回及旧指标；逐项核原点/全部系数/Hz/参数/参考/信息和独立反射、VSWR、dB。
- 真实覆盖非对齐、相等/外伸/空区间、混合模原始基底、legacy顺序、非法选项/噪声、单点下游失败及独占/同路径/父目录错误；核退出码、stderr和无部分输出。旧显式频率组合继续作为兼容控制。
- 新回执/原始输入输出均写`_build/ci/`的新路径，由artifact保存；运行不得修改已跟踪源码或覆盖历史证据。

## 本地与远端证据分开

本地只执行本轮相关的一次干净检查，不重跑未改的旧科学生成器。完整旧门在最终head的必要CI运行，失败在同轮修正并保留原失败证据。all-target检查不等于native运行。

交付报告记录具体runId/URL/jobs/新门及各状态、独立预期、真实输出和未支持边界。最终head源码ZIP必须逐成员读回；Git blob、原工作、实际测试复制件、实际编译/输出各有独立身份。云artifact元数据和本地bundle不能冒充下载云binary或二进制相等。根独立ACCEPT前不增加有效轮数。
