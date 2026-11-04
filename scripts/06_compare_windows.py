"""第 6 步：比较上周同日、前 3 天均值和前 7 天均值。"""

import pandas as pd
from common import output_dir

folder = output_dir()
frame = pd.read_csv(folder / "02_sample.csv", parse_dates=["dt"])
frame = frame.sort_values(["product_id", "dt"]).copy()

# 所有预测都先排除当天，避免使用当天的实际销量。
sales = frame.groupby("product_id")["sale_amount"]
frame["上周同日"] = sales.shift(7)
for days in (3, 7):
    frame[f"前{days}日均值"] = sales.transform(
        lambda values: values.shift(1).rolling(days, min_periods=days).mean()
    )

validation = frame.loc[frame["split"] == "validation"].copy()
results = []
for method in ("上周同日", "前3日均值", "前7日均值"):
    usable = validation.dropna(subset=["sale_amount", method])
    if len(usable) != len(validation):
        raise ValueError(f"{method} 有缺失预测，请检查历史数据。")
    actual = usable["sale_amount"]
    error = usable[method] - actual
    denominator = actual.abs().sum()
    if denominator == 0:
        raise ValueError("实际销量绝对值总和为 0，无法计算 WAPE。")
    results.append({"方法": method, "记录数": len(usable),
                    "MAE": error.abs().mean(),
                    "WAPE": error.abs().sum() / denominator,
                    "偏差率": error.sum() / denominator})

comparison = pd.DataFrame(results).sort_values("WAPE")
destination = folder / "06_window_comparison.csv"
comparison.to_csv(destination, index=False, encoding="utf-8-sig")
print(comparison.to_string(index=False, formatters={
    "MAE": "{:.3f}".format, "WAPE": "{:.1%}".format, "偏差率": "{:.1%}".format
}))
print("结果保存：", destination)
