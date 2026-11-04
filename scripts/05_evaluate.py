"""第 5 步：计算 MAE/WAPE/偏差，并分开看缺货与非缺货日。"""

import pandas as pd

from common import output_dir


folder = output_dir()
frame = pd.read_csv(folder / "04_validation_predictions.csv")


def score(rows: pd.DataFrame, prediction: str) -> dict[str, float | int]:
    observed = rows["sale_amount"]
    predicted = rows[prediction]
    error = predicted - observed
    denominator = observed.abs().sum()
    return {
        "n": len(rows),
        "MAE": error.abs().mean(),
        "WAPE": error.abs().sum() / denominator,
        "bias": error.sum() / denominator,
    }


results = []
for prediction in ["pred_same_weekday", "pred_7day_mean"]:
    for label, subset in [
        ("all", frame),
        ("no_daytime_stockout", frame.loc[~frame["is_stockout"]]),
        ("daytime_stockout", frame.loc[frame["is_stockout"]]),
    ]:
        results.append({"method": prediction, "group": label, **score(subset, prediction)})

metrics = pd.DataFrame(results)
destination = folder / "05_metrics.csv"
metrics.to_csv(destination, index=False, encoding="utf-8-sig")
print(metrics.round(3).to_string(index=False))
print("保存：", destination)

# WAPE 的分母是观察到的实际销量；缺货日真实需求未知。
# 因此这里评估的是实际销量预测，不是完整需求预测。
