# Generated Data Splits

These manifests split generated instances for ALNS hyperparameter tuning.

## Main Split

- `tuning_seed01.txt`: use this set to choose ALNS configurations.
- `test_seed02_seed03.txt`: use this set only after tuning, to compare the chosen configuration against the baseline.

The split is seed-based: `seed01` instances are used for tuning, while matching `seed02` and `seed03` instances are reserved for testing. This keeps the test set independent from configuration selection.

## Optional Set

- `optional_k_sensitivity.txt`: instances that vary `k` and currently only have `seed01`. Keep them out of the main tuning/test split unless you want a separate sensitivity analysis.

## Raw Benchmark Sets

- `raw_cvrplib.txt`: CVRPLIB instances. `K` is inferred from filenames such as `A-n80-k10.vrp`.
- `raw_tsplib_sqrtk.txt`: TSPLIB instances. TSPLIB files do not encode a vehicle count, so this manifest provides `K = round(sqrt(N))` as a second column.

Use the raw sets as separate benchmark sections rather than mixing them into the generated-data test average.

## Example

```powershell
.\.venv\Scripts\python.exe scripts\tune_alns_configs.py --instance-file data\splits\tuning_seed01.txt --seeds 1,2,3 --time-limit 10 --top-k 2 --output-dir output\config_tuning\tuning_seed01
```

After selecting the best final configuration from the tuning set, run that chosen configuration and the baseline on `test_seed02_seed03.txt`.
