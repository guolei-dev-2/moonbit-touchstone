# 新增第一方厂商输入：NXP BFU530W

原真实厂商证据只有 Johanson Technology 的 1,551 频点文件；Agilent E5071C 是该文件的测量仪器，不是另一个器件厂商。本轮补 NXP 的真实 BFU530W 模型输入，保持现有算法不变。两家厂商的有限输入证据不代表全部厂商兼容或外部采用。

## 来源与固定输入

- [NXP 官方 BFU530W 产品页](https://www.nxp.com/products/radio-frequency-rf/legacy-rf/legacy-rf-wideband-transistors/npn-wideband-silicon-rf-transistor:BFU530W)将器件标为 NPN 宽带硅 RF 晶体管，并列出 40 MHz–6 GHz S 参数模型。
- [官方模型 ZIP](https://www.nxp.com/downloads/en/s-parameters/BFU530W_Spar.zip)：页面列 Rev1.0 / 2019-04-23；本次真实 HTTP200，118,380 字节，SHA256 `981d4f80f7ee35d273ce7917708c9f8ffded52372e71dff0ec57f99e41f78928`。
- 包内36份 S2P，本轮只选 `BFU530W_03V3_001mA_SP.s2p`：9,544字节，SHA256 `d4a56bc6b099544c63ddbe25e9a1366935daf1a76bf0e47b0b269bb600ff2a95`。名义偏置3.3V/1mA；文件头带2013-03-26日期及厂商去嵌入说明，原始元数据见 [SOURCE.json](SOURCE.json)。这不是本项目重新进行的 VNA 测量。

## 本次实际核对

当前0.3.0 CLI 用固定 MoonBit 工具链严格构建一次；库、CLI等46份原输入哈希不变。使用现存 scikit-rf 2.1.0 / NumPy 环境仅验证新增文件，未重跑旧30项、1103参考集合或 Johanson 样本。

| 对照 | 逐点范围 | 最大复数绝对误差 |
|---|---|---:|
| 当前 CLI `dump` 与 scikit-rf S | 98频点、392复数值 | 1.6165091241761062e-15 |
| 当前 CLI `rf-convert` S→Y 与 scikit-rf Y | 98频点、392复数值 | 7.928654179053002e-17 S |
| 当前 CLI `normalize` 写出后由 scikit-rf 重新读取 | 98频点、392复数值 | 1.6165091241761062e-15 |

频率（40 MHz–6 GHz）及50Ω参考阻抗完全相等；复数数值容差为 rtol=3e-10、atol=3e-12（Y绝对容差单位为siemens）。三个实际CLI进程均 exit0，详见 [RESULT.json](RESULT.json)、各 `.terminal.json` 与 [BUILD.json](BUILD.json)。这是软件格式与数值核对，不是器件、温度、批次、全部偏置或连续频带认证。

## 数据权利与打包边界

[NXP Terms of Use](https://www.nxp.com/pages/terms-of-use:TERMSOFUSE)未给予把原始模型按本项目MIT许可证再分发的授权；本ZIP内没有额外许可文件。本地原ZIP、选中S2P、完整CLI数值和写出文件只放在 `D:/CodexLocal/ban/work/portfolio-progress-20261027/private-reference-inputs/touchstone-breadth-20261027`，整个目录排除于源码、评委及证据包。项目中只保留URL、哈希、条目/偏置信息、误差和通过摘要、代码与运行元数据。见 [PACKAGE-EXCLUSIONS.json](PACKAGE-EXCLUSIONS.json)。

## 重现

在原项目根目录和既定工具链中构建当前CLI；下载器只访问上述固定NXP地址，哈希变化就停止。必须选择全新、位于分发项目外的本地输入目录。为保留已完成回执，复测输出也使用全新证据子目录（示例名需要尚未存在）。

```powershell
moon build --target js --release --deny-warn
python evidence/public-breadth-20261027/fetch_nxp_curl.py D:/local-private-new-bfu530w
New-Item -ItemType Directory evidence/public-breadth-reproduce-new
Copy-Item evidence/public-breadth-20261027/verify_nxp.py,evidence/public-breadth-20261027/BUILD.json,evidence/public-breadth-20261027/INPUTS-BEFORE.json evidence/public-breadth-reproduce-new/
python evidence/public-breadth-reproduce-new/verify_nxp.py --private-directory D:/local-private-new-bfu530w
```

需使用装有固定 scikit-rf/NumPy 的 Python；本次实际路径和版本已写进 `RESULT.json`。Node默认使用本机固定路径，也可显式传 `--node`。原失败下载尝试保留在 `FETCH-01-FAILURE.json`，`fetch_nxp.py`是该失败路径的记录；复现入口为 `fetch_nxp_curl.py`。没有把失败尝试、旧样本验收或额外未跑的偏置文件写成新增通过。
