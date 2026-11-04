"""第 9 步：分缺货和未缺货记录，比较实际销量预测误差。"""
import pandas as pd
from common import output_dir

folder = output_dir()
data = pd.read_csv(folder / "08_weekday_predictions.csv")
methods = ["same_weekday", "mean_3", "mean_7", "mean_7_weekday"]
if data[methods + ["sale_amount", "is_stockout"]].isna().any().any():
    raise ValueError("验证数据含缺失值，请检查输入。")
if not data["is_stockout"].isin([True, False]).all():
    raise ValueError("is_stockout 应为布尔值。")

results = []
for group, subset in [("无白天缺货", data.loc[~data["is_stockout"]]),
                      ("有白天缺货", data.loc[data["is_stockout"]])]:
    actual = subset["sale_amount"]
    denominator = actual.abs().sum()
    if subset.empty or denominator == 0:
        raise ValueError(f"{group} 没有可用于计算 WAPE 的销量。")
    for method in methods:
        error = subset[method] - actual
        results.append({"group": group, "method": method, "n": len(subset),
                        "MAE": error.abs().mean(),
                        "WAPE": error.abs().sum() / denominator,
                        "bias": error.sum() / denominator})

result = pd.DataFrame(results)
destination = folder / "09_stockout_metrics.csv"
result.to_csv(destination, index=False, encoding="utf-8-sig")
print(result.to_string(index=False, formatters={"MAE": "{:.3f}".format,
      "WAPE": "{:.1%}".format, "bias": "{:.1%}".format}))
print("保存：", destination)
