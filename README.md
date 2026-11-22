# 海天水务 · Home Assistant 集成

把四川海天水务（乐至海天等，微信小程序「云微客服」体系）的水费与用水数据接入 Home Assistant。

## 实体

| 实体 | 说明 |
|---|---|
| `sensor.haitian_water_shui_biao_du_shu` | 水表累计读数（m³，可直接用于能源面板的水） |
| `sensor.haitian_water_shang_qi_yong_shui_liang` | 上期用水量（m³） |
| `sensor.haitian_water_shang_qi_shui_fei` | 上期水费（元） |
| `sensor.haitian_water_dai_jiao_jin_e` | 待缴金额（元，未缴账单合计） |
| `sensor.haitian_water_ben_nian_lei_ji_yong_shui` | 本年累计用水（m³） |
| `sensor.haitian_water_yu_cun_jin_e` | 预存金额（元） |
| `binary_sensor.haitian_water_qian_fei` | 是否欠费 |

读数实体带 `近12期账单` 属性（月份、读数、用水量、金额、缴费状态），可以直接做卡片。

## 工作原理

港华那种「扫码一次就能长期用」的模式在这里不成立 —— 海天的小程序令牌来自微信登录（`jsCode + encryptedData`），无法在服务端复现。但它的接口提供了 `POST /api/user/relogin`，只要手里有一枚**有效令牌**，就能不断换取新令牌。

所以集成的策略是：

1. 配置时填入一枚抓到的 `access_token`（一次性）
2. 之后每 10 分钟调一次 `relogin` 滚动续期，并把新令牌写回配置条目
3. 只要 HA 不长时间停机，令牌链就不会断
4. 万一断了，HA 会弹出「重新授权」，再填一次令牌即可

## 获取 access_token

微信打开「乐至海天水务」公众号 → **营业大厅** → **微网厅** → 授权登录 → 打开账单页。然后用抓包工具（Charles / Reqable / mitmproxy / Stream）抓 `tchal.haitianshuiwu.cn` 的请求，任选一条请求头里的：

```
Authorization: Bearer eyJhbGciOiJBMjU2S1ci...
```

`Bearer ` 后面那一整串就是令牌（约 2000 字符，以 `eyJhbGciOiJBMjU2S1ci` 开头）。

## 安装

HACS → 集成 → 右上角 ⋮ → 自定义存储库 → 填入本仓库地址 → 类别选「集成」→ 添加 → 搜索「海天水务」→ 下载 → 重启 Home Assistant。

## 已知限制

- 令牌链一旦断裂必须人工补令牌，无法全自动恢复
- 户号必须在微信里已绑定（小程序「绑定表卡」）
- 接口无官方文档，海天改版可能需要跟进修复

## 免责声明

本项目仅读取本人账户的账单数据，不含任何缴费/变更操作。接口为逆向所得，稳定性取决于上游。
