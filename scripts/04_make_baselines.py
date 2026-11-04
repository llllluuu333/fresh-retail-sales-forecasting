"""第 4 步：只用过去的销量生成两个简单预测。"""

import pandas as pd

from common import output_dir


folder = output_dir()
frame = pd.read_csv(folder / "02_sample.csv", parse_dates=["dt"])
frame = frame.sort_values(["product_id", "dt"]).copy()

# 上周同日：shift(7) 明确排除当天及其后日期。
frame["pred_same_weekday"] = frame.groupby("product_id")["sale_amount"].shift(7)

# 前 7 日平均：先 shift(1) 排除当天，再计算 7 天滚动平均。
frame["pred_7day_mean"] = frame.groupby("product_id")["sale_amount"].transform(
    lambda sales: sales.shift(1).rolling(window=7, min_periods=7).mean()
)

# 前 7 天没有足够历史，预测为空；只导出最后 14 天做评估。
validation = frame.loc[frame["split"] == "validation"].copy()
destination = folder / "04_validation_predictions.csv"
validation.to_csv(destination, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
print(f"验证记录 {len(validation)} 行；保存：{destination}")
print("预测缺失数：", validation[["pred_same_weekday", "pred_7day_mean"]].isna().sum().to_dict())

# 思考：滚动预测用到了前一个验证日的实际销量，适用什么业务场景？
