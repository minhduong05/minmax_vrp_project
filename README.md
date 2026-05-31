# Min-Max Vehicle Routing with ALNS

Dự án này cài đặt thuật toán **Adaptive Large Neighborhood Search (ALNS)** cho bài toán **Min Max Vehicle Routing** trong mini project.

## 1. Bài toán

Có `N` điểm cần thu gom bưu kiện và `K` bưu tá/xe xuất phát từ depot `0`. Cần chia các điểm `1..N` thành `K` route và sắp thứ tự đi sao cho route dài nhất là nhỏ nhất.

Mỗi route `k` có dạng:

```text
x[1] = 0, x[2], ..., x[l_k]
```

trong đó `x[2]..x[l_k]` là các điểm thu gom. Mặc định code đánh giá đúng theo format này, tức không tự cộng cạnh quay lại depot.

Hàm mục tiêu chính:

```text
minimize max(route_length[k])
```

Tie-break phụ:

```text
nếu max route bằng nhau, ưu tiên total distance nhỏ hơn
```

## 2. Cấu trúc code

```text
minmax_vrp_project/
├── pyproject.toml
├── main.py
├── README.md
├── examples/
│   └── sample.txt
└── minmax_vrp/
    ├── __init__.py
    ├── acceptance.py       # Simulated Annealing acceptance
    ├── adaptive.py         # cập nhật trọng số operators
    ├── alns.py             # vòng lặp ALNS chính
    ├── cli.py              # command line interface
    ├── construction.py     # tạo lời giải ban đầu
    ├── destroy.py          # destroy operators
    ├── io.py               # đọc input, ghi output
    ├── local_search.py     # 2-opt, relocate, swap
    ├── models.py           # Instance, Solution, Evaluation
    ├── operators_utils.py  # hàm delta insert/remove
    └── repair.py           # repair operators
```

## 3. Destroy operators

Các toán tử phá lời giải:

- `RandomRemoval`: xóa ngẫu nhiên một số điểm.
- `WorstRemoval`: xóa các điểm gây chi phí lớn.
- `LongestRouteRemoval`: tập trung phá route dài nhất.
- `RelatedRemoval`: xóa cụm điểm gần nhau.
- `RouteRemoval`: xóa một phần/toàn bộ một route.

## 4. Repair operators

Các toán tử sửa lời giải:

- `GreedyMinMaxInsertion`: chèn điểm vào vị trí làm `max(route_length)` nhỏ nhất.
- `RegretInsertion`: ưu tiên điểm khó chèn trước.
- `BalancedInsertion`: cân bằng giữa giảm route dài nhất và chi phí chèn.

## 5. Local search sau repair

Sau repair, solver có thể chạy local search nhỏ:

- relocate từ route dài nhất,
- swap giữa route dài nhất và route khác,
- 2-opt trong các route dài.

## 6. Cài đặt

Dùng `uv`:

```bash
uv sync
```

Hoặc dùng pip:

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows PowerShell/CMD
# source .venv/bin/activate  # macOS/Linux
pip install -e .
```

`pyproject.toml` có khai báo `ortools` để phù hợp hướng tối ưu lập kế hoạch, dù bản ALNS hiện tại không phụ thuộc trực tiếp vào OR-Tools.

## 7. Chạy thử

```bash
python main.py examples/sample.txt --time-limit 5 --seed 42 --verbose
```

Hoặc sau khi install package:

```bash
minmax-vrp examples/sample.txt --time-limit 5 --seed 42 --verbose
```

Ghi output ra file:

```bash
python main.py examples/sample.txt -o output.txt --time-limit 10 --verbose
```

Nếu muốn tính cả cạnh quay về depot trong lúc đánh giá:

```bash
python main.py examples/sample.txt --return-to-depot --time-limit 5
```

## 8. Format input

```text
N K
row_0: d[0][0] d[0][1] ... d[0][N]
row_1: d[1][0] d[1][1] ... d[1][N]
...
row_N: d[N][0] d[N][1] ... d[N][N]
```

Trong đó ma trận khoảng cách có kích thước `(N+1) x (N+1)`.

## 9. Format output

```text
K
l1
0 ...
l2
0 ...
...
```

Mỗi route bắt đầu bằng `0`.

Ví dụ output cho 2 route:

```text
2
3
0 5 2
5
0 4 1 3 6
```
