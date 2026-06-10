# 智能定投双方案

## 方案一：综合分 S（`score_only`）

- 每期投入 `P × f(S)`，S 低加投、S 高减投。
- 回测**不使用**回撤加成（仅 f(S)）。
- 可调：激进倍数 M（1.5× / 2×）。
- 回测支持「等额总投入」对比。

## 方案二：日常 + 备用子弹（`split_reserve`）

**不使用综合分 S。**

每期计划金额 P 拆分为：

| 参数 | 含义 |
|------|------|
| X `routine_pct` | 日常定投占比，每期固定投入 `P×X`（入场状态下） |
| Y `reserve_pct` | 备用子弹占比，每期 `P×Y` 进入子弹池 |
| Z `drawdown_trigger` | 相对窗口高点回撤达 Z 后，按深度从池中加仓 |
| `full_deploy_depth` | 回撤达到该深度时，本期打光池中子弹 |
| `lookback_days` | 高点窗口（252≈52 周） |
| T `take_profit_pct` | **可选**；持仓收益达 T 后**全部卖出**并入子弹池，之后**不再日常定投**，直到回撤再次达 Z 后按 X/Y 重新入场；默认关闭 |

### 方案二状态机

1. **正常入场**：X 日常 + Y 存池；回撤 ≥ Z 时按深度从池加仓  
2. **止盈（T 启用）**：当 `持仓市值 / 持仓成本 - 1 ≥ T` 时清仓，资金并入子弹池，进入「等 Z」  
3. **等 Z**：每期计划 P **全部入池**，不买标的；回撤再次 ≥ Z 时恢复步骤 1  

### 回测口径修正

- 智能策略**期末市值** = 持仓市值 + 子弹池现金（此前仅计持仓会低估总财富）

## 界面

- **定投** / **回测** 页顶部 TAB 切换方案。
- 方案二参数写入 `localStorage`，回测通过 `sr_*` 查询参数传给 API。

## 回测：定投总期数

- 参数 `max_periods`：仅回测**最近 N 期**定投日（两套方案共用）；不传或 `0` = 全样本。

## API

- `GET /api/v1/dca/scheme-defaults`
- `POST /api/v1/dca/preview`：`dca_mode=split_reserve` + `routine_pct`、`take_profit_pct`、`waiting_reentry` 等
- `GET /api/v1/backtest/{id}`：`max_periods`、`sr_take_profit_pct`、`sr_routine_pct` 等
