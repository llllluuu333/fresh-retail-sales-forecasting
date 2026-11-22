"""Run a small invented forecast example without downloading retail data."""
import json
import pandas as pd
from forecasting.core import prepare, fit_weekday_factors, predict, evaluate


def synthetic_data():
    """Two made-up product series; weekday pattern and drift are assumed."""
    factors = (0.8, 0.9, 1.0, 1.0, 1.1, 1.2, 1.0)
    rows = []
    for product, scale in ((101, 10.0), (102, 20.0)):
        for i, day in enumerate(pd.date_range("2024-01-01", periods=21)):
            rows.append({"store_id": 1, "product_id": product, "dt": day,
                         "sale_amount": scale * factors[i % 7] + 0.2 * (i // 7),
                         "split": "training" if i < 14 else "validation"})
    return pd.DataFrame(rows)


def run():
    data = prepare(synthetic_data())
    factors = fit_weekday_factors(data)
    predicted = predict(data, factors, window=7)
    validation = predicted.loc[predicted["split"] == "validation"]
    return {"scope": "Synthetic illustration only; not the real dataset or business performance.",
            "description": "14 training days, then seven one-day forecasts updated with observed sales",
            "metrics": {name: evaluate(validation, name)
                        for name in ("baseline", "adjusted")}}


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
