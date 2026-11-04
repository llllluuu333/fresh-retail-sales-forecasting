"""Run a configurable validation experiment from an existing sample CSV."""
import argparse
import json
from pathlib import Path
import pandas as pd
from forecasting.core import prepare, fit_weekday_factors, predict, evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('artifacts/02_sample.csv'))
    parser.add_argument('--output', type=Path, default=Path('artifacts/experiment'))
    parser.add_argument('--window', type=int, default=7)
    args = parser.parse_args()
    data = prepare(pd.read_csv(args.input))
    factors = fit_weekday_factors(data)
    predictions = predict(data, factors, args.window)
    validation = predictions.loc[predictions['split'] == 'validation']
    metrics = {name: evaluate(validation, name) for name in ['baseline', 'adjusted']}
    args.output.mkdir(parents=True, exist_ok=True)
    validation.to_csv(args.output / 'predictions.csv', index=False)
    (args.output / 'metrics.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    main()
