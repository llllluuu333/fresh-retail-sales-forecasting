"""第 3 步：画每日销量与缺货比例，先观察，再提假设。"""

import matplotlib

matplotlib.use("Agg")  # 保存图片，不要求弹出绘图窗口。
import matplotlib.pyplot as plt
import pandas as pd

from common import output_dir


folder = output_dir()
sample = pd.read_csv(folder / "02_sample.csv", parse_dates=["dt"])

# 对同一门店的 20 个商品按日期汇总。
daily = sample.groupby("dt", as_index=False).agg(
    observed_sales=("sale_amount", "sum"),
    stockout_share=("is_stockout", "mean"),
)
validation_start = sample.loc[sample["split"] == "validation", "dt"].min()

fig, axes = plt.subplots(2, 1, sharex=True, figsize=(10, 6), constrained_layout=True)
axes[0].plot(daily["dt"], daily["observed_sales"], color="#1769aa")
axes[0].set_ylabel("Normalized sales")
axes[1].plot(daily["dt"], daily["stockout_share"], color="#c65d25")
axes[1].set_ylabel("Stockout share")
axes[1].set_ylim(0, 1)
axes[1].set_xlabel("Date")
for axis in axes:
    axis.axvline(validation_start, color="black", linestyle="--")
    axis.grid(alpha=0.25)

destination = folder / "03_daily_trend.png"
fig.savefig(destination, dpi=160)
plt.close(fig)
print("保存：", destination)

# 思考：两条线一起波动，能否证明缺货导致销量变化？
