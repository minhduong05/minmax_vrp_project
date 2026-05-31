# Runners

Dự án có 2 runner chính trong `scripts/`.

## Single Run

Dùng khi muốn chạy đúng 1 thuật toán trên đúng 1 file `.txt`.

```powershell
.\.venv\Scripts\python.exe scripts\run_single_algorithm.py data\hustack\tc12.txt --algorithm alns --time-limit 5
```

Output được ghi vào `outputs/single_run/`:

- `<instance>_<algorithm>_solution.txt`
- `<instance>_<algorithm>_summary.csv`
- `<instance>_<algorithm>_summary.txt`

Summary có các thông số:

- `max_route`
- `min_route`
- `total_distance`
- `balance`
- `route_lengths`
- `runtime`
- `iterations`
- `feasible`
- `reference_*` và `gap` nếu data có reference.

Options hay dùng:

```powershell
--algorithm alns
--time-limit 5
--seed 99
--local-search
--return-to-depot
--no-return-to-depot
```

## Benchmark Run

Dùng khi muốn chạy nhiều data, nhiều thuật toán, và so sánh kết quả.

Chạy 4 thuật toán trên tất cả prepared data:

```powershell
.\.venv\Scripts\python.exe scripts\run_algorithm_benchmarks.py --algorithms all --time-limit 5
```

Chạy 1 thuật toán trên tất cả prepared data:

```powershell
.\.venv\Scripts\python.exe scripts\run_algorithm_benchmarks.py --algorithms alns --time-limit 5
```

Chạy 4 thuật toán trên 1 file:

```powershell
.\.venv\Scripts\python.exe scripts\run_algorithm_benchmarks.py data\hustack\tc12.txt --algorithms all --time-limit 5
```

Chạy 4 thuật toán trên 1 folder data:

```powershell
.\.venv\Scripts\python.exe scripts\run_algorithm_benchmarks.py data\hustack --algorithms all --time-limit 5
```

Benchmark runner luôn ghi 7 CSV trong `outputs/logs/`.
