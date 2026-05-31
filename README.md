# Dự Án Min-Max VRP

Dự án này dùng để đọc dữ liệu bài toán Min-Max Vehicle Routing Problem, chạy
nhiều thuật toán giải, và so sánh kết quả theo mục tiêu min-max.

Bài toán có:

- `N` điểm cần phục vụ, đánh số `1..N`.
- `K` tuyến đường.
- depot là node `0`.
- mỗi tuyến bắt đầu từ `0`.
- mục tiêu chính là tối thiểu hóa tuyến dài nhất: `max_route`.

## Chạy Nhanh

Chạy 1 thuật toán trên đúng 1 file `.txt` và ghi kết quả vào
`outputs/single_run/`:

```powershell
.\.venv\Scripts\python.exe scripts\run_single_algorithm.py data\hustack\tc12.txt --algorithm alns --time-limit 5
```

Chạy benchmark nhiều thuật toán trên nhiều bộ dữ liệu và ghi 7 file CSV vào
`outputs/logs/`:

```powershell
.\.venv\Scripts\python.exe scripts\run_algorithm_benchmarks.py --algorithms all --time-limit 5
```

Chạy test:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Nếu `.venv` chưa có `pytest`, hãy cài dependency dev trước.

## Cây Thư Mục Dự Án

```text
minmax_vrp_project/
|-- README.md                         # Tổng quan dự án, cách chạy nhanh, và cấu trúc thư mục.
|-- pyproject.toml                    # Metadata Python package, dependencies, cấu hình pytest.
|-- uv.lock                           # Lock file môi trường/dependencies nếu dùng uv.
|-- .gitignore                        # Bỏ qua cache Python, .venv, output CSV/log cục bộ.
|
|-- minmax_vrp/                       # Source code chính của package giải Min-Max VRP.
|   |-- __init__.py                   # Đánh dấu package Python.
|   |-- cli.py                        # CLI cơ bản cho 1 input, 1 thuật toán, output tùy chọn.
|   |-- io.py                         # Đọc input .txt và ghi solution theo format dự án.
|   |-- models.py                     # Instance, Solution, Evaluation, feasibility, objective.
|   |
|   |-- algorithms/                   # Tất cả thuật toán được đăng ký tại đây.
|   |   |-- __init__.py               # Export registry/config để import gọn.
|   |   |-- base.py                   # Interface chung: AlgorithmConfig, AlgorithmResult.
|   |   |-- common.py                 # Helper dùng chung giữa các thuật toán.
|   |   |-- registry.py               # Bảng đăng ký tên thuật toán -> class solver.
|   |   |
|   |   |-- alns/                     # Adaptive Large Neighborhood Search.
|   |   |   |-- __init__.py           # Export ALNSAlgorithm.
|   |   |   |-- adapter.py            # Adapter để ALNS khớp interface chung.
|   |   |   |-- solver.py             # Vòng lặp ALNS chính.
|   |   |   |-- construction.py       # Khởi tạo nghiệm ban đầu.
|   |   |   |-- destroy.py            # Các destroy operators.
|   |   |   |-- repair.py             # Các repair operators.
|   |   |   |-- local_search.py       # Cải thiện nghiệm cục bộ.
|   |   |   |-- adaptive.py           # Cập nhật trọng số operator.
|   |   |   |-- acceptance.py         # Tiêu chí chấp nhận simulated annealing.
|   |   |   |-- operators_utils.py    # Tính delta chèn/xóa và helper operator.
|   |   |
|   |   |-- greedy_balanced/          # Heuristic chèn điểm để cân bằng tuyến.
|   |   |   |-- __init__.py           # Export GreedyBalancedAlgorithm.
|   |   |   |-- solver.py             # Solver greedy balanced.
|   |   |
|   |   |-- nearest_insertion/        # Heuristic nearest insertion.
|   |   |   |-- __init__.py           # Export NearestInsertionAlgorithm.
|   |   |   |-- solver.py             # Solver nearest insertion.
|   |   |
|   |   |-- round_robin/              # Baseline chia điểm lần lượt vào các tuyến.
|   |       |-- __init__.py           # Export RoundRobinAlgorithm.
|   |       |-- solver.py             # Solver round-robin.
|
|-- data/                             # Dữ liệu input và reference đã convert cho dự án.
|   |-- HUONG_DAN.md                  # Ghi chú nguồn dữ liệu và cách convert.
|   |-- validation_summary.csv        # Tóm tắt validate data pipeline.
|   |
|   |-- hustack/                      # Data HUSTACK đã convert sang .txt.
|   |   |-- tc*.txt                   # Các input instance.
|   |   |-- reference.csv             # Kết quả jury dùng để so sánh.
|   |   |-- reference_jury.csv        # Reference gốc/bổ sung từ jury.
|   |
|   |-- mtsplib_minmax/               # Data MinMax mTSP có reference literature/tours.
|   |   |-- *_k*.txt                  # Input instance theo số tuyến k.
|   |   |-- reference.csv             # Reference chính dùng để compare.
|   |   |-- reference_all.csv         # Reference mở rộng.
|   |
|   |-- tsplib_converted/             # TSPLIB convert sang min-max input.
|   |   |-- *_k*.txt                  # Input instance sinh từ TSPLIB.
|   |
|   |-- cvrplib_converted/            # CVRPLIB convert sang input của dự án.
|   |   |-- *.txt                     # Input instance sinh từ CVRPLIB.
|   |
|   |-- raw/                          # Dữ liệu gốc để reproduce pipeline.
|       |-- tsplib/                   # File .tsp gốc.
|       |-- cvrplib/                  # File .vrp gốc.
|       |-- mtsplib_minmax/           # Tour/reference gốc của MTSPLIB.
|       |-- hustack_jury/             # Output jury gốc HUSTACK.
|
|-- scripts/                          # Script vận hành dự án: data pipeline, single run, benchmark.
|   |-- benchmark_data_utils.py       # Parser/helper chung cho TSPLIB/CVRPLIB conversion.
|   |-- download_raw_benchmarks.py    # Tải raw benchmark về data/raw.
|   |-- install_report_benchmarks.py  # Convert raw benchmarks sang format .txt của dự án.
|   |-- build_mtsplib_reference_from_tours.py # Build reference MTSPLIB từ tour files.
|   |-- build_hustack_reference.py    # Build reference HUSTACK từ jury outputs.
|   |-- validate_data_pipeline.py     # Kiểm tra data convert và schema reference.
|   |-- run_single_algorithm.py       # Chạy 1 thuật toán trên đúng 1 file .txt.
|   |-- run_algorithm_benchmarks.py   # Chạy benchmark nhiều data/algorithm, ghi 7 CSV logs.
|
|-- outputs/                          # Kết quả sinh ra khi chạy script; thường là artifact cục bộ.
|   |-- single_run/                   # Output cho 1 file + 1 thuật toán.
|   |   |-- *_solution.txt            # Solution theo format dự án.
|   |   |-- *_summary.csv             # Summary 1 dòng có metric và reference gap.
|   |   |-- *_summary.txt             # Bản đọc nhanh cho người dùng.
|   |
|   |-- logs/                         # CSV log benchmark hàng loạt.
|   |   |-- algorithm_comparison.csv  # Toàn bộ row benchmark.
|   |   |-- alns_results.csv          # Chỉ các row của ALNS.
|   |   |-- round_robin_results.csv   # Chỉ các row của round_robin.
|   |   |-- greedy_balanced_results.csv # Chỉ các row của greedy_balanced.
|   |   |-- nearest_insertion_results.csv # Chỉ các row của nearest_insertion.
|   |   |-- comparison_with_reference.csv # Các row có reference.csv để so gap.
|   |   |-- comparison_without_reference.csv # Các row không có reference.
|   |
|   |-- experiments/                  # Solution/output theo lô benchmark nhiều instance.
|
|-- tests/                            # Pytest suite: test parser, objective, solver smoke, helper.
|   |-- README.md                     # Giải thích tests dùng để làm gì.
|   |-- test_io_models.py             # Test input parser, objective, feasibility.
|   |-- test_algorithms_smoke.py      # Test 4 thuật toán trả về solution feasible.
|   |-- test_benchmark_helpers.py     # Test reference matching, gap, status.
|
|-- docs/                             # Tài liệu hướng dẫn chi tiết cho workflow trong repo.
    |-- RUNNERS.md                    # Cách dùng single run và benchmark runner.
    |-- OUTPUTS.md                    # Ý nghĩa outputs/single_run, outputs/logs, 7 CSV.
    |-- TESTS.md                      # Tests là gì, khi nào cần chạy, cách viết test mới.
```

## Các Thuật Toán

Tên thuật toán hiện có:

```text
alns
round_robin
greedy_balanced
nearest_insertion
```

Tất cả thuật toán được đăng ký trong:

```text
minmax_vrp/algorithms/registry.py
```

## Single Run

Dùng khi bạn muốn xem kỹ một kết quả duy nhất.

```powershell
.\.venv\Scripts\python.exe scripts\run_single_algorithm.py data\hustack\tc12.txt --algorithm alns --time-limit 5
```

Script sẽ in metric ra terminal và ghi vào `outputs/single_run/`:

- solution `.txt`
- summary `.csv`
- summary `.txt`

## Benchmark

Dùng khi bạn muốn chạy nhiều data hoặc nhiều thuật toán.

```powershell
.\.venv\Scripts\python.exe scripts\run_algorithm_benchmarks.py --algorithms all --time-limit 5
```

Sau mỗi lần chạy, `outputs/logs/` có 7 file CSV:

- `algorithm_comparison.csv`
- `alns_results.csv`
- `round_robin_results.csv`
- `greedy_balanced_results.csv`
- `nearest_insertion_results.csv`
- `comparison_with_reference.csv`
- `comparison_without_reference.csv`

## Reference

Nếu dataset có `reference.csv`, runner sẽ tự so sánh:

- `reference_max_route`
- `max_route_gap`
- `max_route_gap_percent`
- `status`

Nếu reference yêu cầu `return_to_depot=yes`, runner tự bật mode return-to-depot,
trừ khi bạn ép bằng `--return-to-depot` hoặc `--no-return-to-depot`.

## Thêm Thuật Toán Mới

Tạo folder mới trong:

```text
minmax_vrp/algorithms/my_solver/
```

Class solver nên theo interface trong:

```python
from minmax_vrp.algorithms.base import AlgorithmConfig, AlgorithmResult, SolverAlgorithm
```

Sau đó đăng ký trong:

```text
minmax_vrp/algorithms/registry.py
```

Khi đã đăng ký, có thể chạy:

```powershell
.\.venv\Scripts\python.exe scripts\run_single_algorithm.py data\hustack\tc12.txt --algorithm my_solver
```
