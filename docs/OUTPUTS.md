# Outputs

`outputs/` là nơi chứa kết quả sinh ra khi chạy runner. Thư mục này không phải
input của thuật toán.

## outputs/single_run

Dùng cho workflow 1 file `.txt` + 1 thuật toán.

Mỗi lần chạy `scripts/run_single_algorithm.py`, thư mục này sẽ có:

```text
<instance>_<algorithm>_solution.txt
<instance>_<algorithm>_summary.csv
<instance>_<algorithm>_summary.txt
```

`solution.txt` dùng format output của dự án.

`summary.csv` dùng để import vào spreadsheet hoặc xử lý bằng script.

`summary.txt` dùng để đọc nhanh bằng mắt người.

## outputs/logs

Dùng cho benchmark hàng loạt bằng `scripts/run_algorithm_benchmarks.py`.

Runner sinh 7 CSV:

```text
algorithm_comparison.csv
alns_results.csv
round_robin_results.csv
greedy_balanced_results.csv
nearest_insertion_results.csv
comparison_with_reference.csv
comparison_without_reference.csv
```

Ý nghĩa:

- `algorithm_comparison.csv`: gom tất cả kết quả đã chạy.
- `<algorithm>_results.csv`: log riêng từng thuật toán.
- `comparison_with_reference.csv`: chỉ các row có reference để so gap.
- `comparison_without_reference.csv`: các row không có reference, chỉ xem metric solver.

Nếu chỉ chạy 1 thuật toán, các file thuật toán khác vẫn được tạo nhưng có thể
chỉ có header. Như vậy cấu trúc log luôn ổn định.

## outputs/experiments

Dùng để lưu solution/output theo lô benchmark nhiều instance. File trong đây là
artifact thực nghiệm, có thể sinh lại bằng runner.
