"""第 8 步：用训练期星期系数调整预测，并与原基准比较。"""
import pandas as pd
from common import output_dir

folder = output_dir()
frame = pd.read_csv(folder / "02_sample.csv", parse_dates=["dt"])
frame = frame.sort_values(["product_id", "dt"]).copy()
frame["weekday"] = frame["dt"].dt.day_of_week
train = frame.loc[frame["split"] == "training"]

# 仅使用训练期估计各星期的平均水平及其与总体平均的比值。
overall_mean = train["sale_amount"].mean()
if overall_mean <= 0:
    raise ValueError("训练期平均销量必须大于 0。")
factors = train.groupby("weekday")["sale_amount"].mean() / overall_mean
if len(factors) != 7:
    raise ValueError("训练期未覆盖全部星期。")
frame["weekday_factor"] = frame["weekday"].map(factors)

# 每天预测下一天，可使用此前验证日已经发生的实际销量。
sales = frame.groupby("product_id")["sale_amount"]
frame["same_weekday"] = sales.shift(7)
frame["mean_3"] = sales.transform(lambda x: x.shift(1).rolling(3, min_periods=3).mean())
frame["mean_7"] = sales.transform(lambda x: x.shift(1).rolling(7, min_periods=7).mean())
frame["mean_7_weekday"] = frame["mean_7"] * frame["weekday_factor"]

validation = frame.loc[frame["split"] == "validation"].copy()
methods = ["same_weekday", "mean_3", "mean_7", "mean_7_weekday"]
if validation[methods + ["sale_amount"]].isna().any().any():
    raise ValueError("验证集存在缺失实际值或预测值。")
actual = validation["sale_amount"]
denominator = actual.abs().sum()
if denominator == 0:
    raise ValueError("实际销量绝对值总和为 0，无法计算 WAPE。")
results = []
for method in methods:
    error = validation[method] - actual
    results.append({"method": method, "n": len(validation),
                    "MAE": error.abs().mean(),
                    "WAPE": error.abs().sum() / denominator,
                    "bias": error.sum() / denominator})
results = pd.DataFrame(results).sort_values("WAPE")
factors.rename("factor").to_csv(folder / "08_weekday_factors.csv", encoding="utf-8-sig")
results.to_csv(folder / "08_weekday_comparison.csv", index=False, encoding="utf-8-sig")
validation.to_csv(folder / "08_weekday_predictions.csv", index=False, encoding="utf-8-sig")
print("训练期星期系数（周一=0）：")
print(factors.round(3).to_string())
print("\n验证期比较：")
print(results.to_string(index=False, formatters={"MAE": "{:.3f}".format,
      "WAPE": "{:.1%}".format, "bias": "{:.1%}".format}))
