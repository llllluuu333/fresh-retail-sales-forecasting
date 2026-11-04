"""第 7 步：只用训练期数据分析星期与销量的关系。"""
import pandas as pd
from common import output_dir

folder = output_dir()
sample = pd.read_csv(folder / "02_sample.csv", parse_dates=["dt"])
training = sample.loc[sample["split"] == "training"].copy()

# 周一是 0，周日是 6。
training["weekday"] = training["dt"].dt.day_of_week
summary = training.groupby("weekday", as_index=False).agg(
    records=("sale_amount", "size"),
    avg_sales=("sale_amount", "mean"),
    stockout_share=("is_stockout", "mean"),
)
summary["weekday_name"] = summary["weekday"].map(
    {0: "周一", 1: "周二", 2: "周三", 3: "周四", 4: "周五", 5: "周六", 6: "周日"}
)
summary = summary[["weekday_name", "records", "avg_sales", "stockout_share"]]
destination = folder / "07_weekday_summary.csv"
summary.to_csv(destination, index=False, encoding="utf-8-sig")
print(summary.to_string(index=False, formatters={
    "avg_sales": "{:.3f}".format, "stockout_share": "{:.1%}".format,
}))
print("保存：", destination)
