# Power BI：全量门店销量预测看板

本项目有两个分析范围：早期样例为一个门店的 20 个商品，用于学习和调试；全量实验覆盖 898 个门店、50,000 条门店—商品序列、485 万条原始记录。全量报表在 Power BI Desktop 中已打开并刷新验证。

## 如何复现

1. 按仓库主 README 下载原始数据并运行 `python run_pipeline.py`。其中 `scripts/12_full_population.py` 计算全量滚动预测、评估和门店汇总，`scripts/13_export_full_powerbi.py` 生成 `artifacts/powerbi_full_model/` 下的报表数据。原始数据与生成结果不会提交 Git。
2. 在仓库根目录运行 `python powerbi/build_project.py --data-folder "你的仓库绝对路径/artifacts/powerbi_full_model"`，然后用 Power BI Desktop 打开 `powerbi/Retail.pbip` 并点击 Refresh。提交前运行 `python powerbi/build_project.py` 恢复占位路径，避免公开本机路径。
3. 在 Period 选择 test：基线 WAPE 应为 34.6%，星期调整后为 33.0%；选择 validation：分别为 34.0% 和 32.6%。未选时期时，卡片显示两段合并结果。
4. 本全量报告中 Product 切片器实际展示的是 Store / all products，选择后是门店维度，不是单商品维度。第二页的 Product-level 表格同样是门店汇总。

## 看板口径

全量原始数据用于建立预测和数据质量检查。报表仅展示验证和测试共 21 天的结果，并按门店、日期和是否缺货预聚合；保留逐商品绝对误差之和，因此 WAPE = 绝对误差总和 / 实际销量总和，而非先汇总预测和实际再计算误差，也不是平均各门店 WAPE。白天缺货比例是存在白天缺货的商品日记录数 / 商品日记录总数。

模型使用过去 7 天平均销量预测下一天；星期系数仅用验证期之前的数据计算。每一天预测可使用此前实际销量，因此是每天滚动更新的一日预测，不是一次预测未来七天。销量已归一化，不是实际件数或未受缺货影响的真实需求。

测试期此前已在样例实验中查看，因此全量结果属于探索性评估，不能作为完全独立的最终测试。更严格的后续验证需要新的未触碰时间窗口或独立数据。

## 代码学习

- `scripts/12_full_population.py`：DuckDB SQL、窗口函数、滚动预测、时间切分和全量误差聚合。
- `scripts/13_export_full_powerbi.py`：报表事实表、维度表、预聚合和数据粒度。
- `powerbi/build_project.py`：Power Query 导入、关系模型、报告和可视化结构。
- `powerbi/measures.dax`：SUM、DIVIDE、CALCULATE、筛选上下文及 WAPE。

数据来源与许可见主 README；不要把本机数据路径、缓存或原始数据提交到公开仓库。
