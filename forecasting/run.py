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
    parser.add_argument('--overwrite', action='store_true', help='replace existing result files')
    args = parser.parse_args()
    paths = [args.output / 'predictions.csv', args.output / 'metrics.json']
    if any(path.resolve() == args.input.resolve() for path in paths):
        parser.error('Input and output files must differ')
    if not args.overwrite and any(path.exists() for path in paths):
        parser.error('Result file already exists; choose another output directory or pass --overwrite')
    data = prepare(pd.read_csv(args.input))
    factors = fit_weekday_factors(data)
    predictions = predict(data, factors, args.window)
    validation = predictions.loc[predictions['split'] == 'validation']
    metrics = {name: evaluate(validation, name) for name in ['baseline', 'adjusted']}
    args.output.mkdir(parents=True, exist_ok=True)
    mode = 'w' if args.overwrite else 'x'
    with paths[0].open(mode, encoding='utf-8', newline='') as handle:
        validation.to_csv(handle, index=False)
    with paths[1].open(mode, encoding='utf-8', newline='') as handle:
        handle.write(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    main()
