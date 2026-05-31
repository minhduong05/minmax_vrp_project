# Min-Max VRP Project

Repository này dùng để chạy và so sánh nhiều thuật toán cho bài toán Min-Max
VRP: có `N` bưu kiện, `K` route, depot là node `0`, cần chia các bưu kiện
`1..N` vào `K` route sao cho route dài nhất nhỏ nhất.

## Cấu Trúc Thư Mục

```text
minmax_vrp_project/
├── main.py
├── pyproject.toml
├── README.md
├── minmax_vrp/
│   ├── cli.py
│   ├── io.py
│   ├── models.py
│   └── algorithms/
│       ├── base.py
│       ├── common.py
│       ├── registry.py
│       ├── alns/
│       │   ├── solver.py
│       │   ├── adapter.py
│       │   ├── destroy.py
│       │   ├── repair.py
│       │   ├── local_search.py
│       │   └── ...
│       ├── round_robin/
│       │   └── solver.py
│       ├── greedy_balanced/
│       │   └── solver.py
│       └── nearest_insertion/
│           └── solver.py
├── data/
│   ├── raw/
│   ├── hustack/
│   ├── mtsplib_minmax/
│   ├── tsplib_converted/
│   └── cvrplib_converted/
├── scripts/
└── outputs/
```

## Đẩy Thuật Toán Mới Vào Đâu?

Mỗi thuật toán phải nằm trong một folder riêng dưới:

```text
minmax_vrp/algorithms/
```

Ví dụ muốn thêm thuật toán `my_solver`, tạo:

```text
minmax_vrp/algorithms/my_solver/
├── __init__.py
└── solver.py
```

Trong `solver.py`, class thuật toán nên kế thừa interface chung:

```python
from minmax_vrp.algorithms.base import AlgorithmConfig, AlgorithmResult, SolverAlgorithm
```

Class cần có:

```python
class MySolverAlgorithm(SolverAlgorithm):
    name = "my_solver"

    def __init__(self, config: AlgorithmConfig) -> None:
        self.config = config

    def solve(self, instance):
        ...
        return AlgorithmResult(...)
```

Sau đó đăng ký thuật toán trong:

```text
minmax_vrp/algorithms/registry.py
```

Thêm import:

```python
from .my_solver import MySolverAlgorithm
```

và thêm vào `ALGORITHMS`:

```python
ALGORITHMS = {
    ...
    MySolverAlgorithm.name: MySolverAlgorithm,
}
```

Sau khi đăng ký, chạy được bằng:

```powershell
.\.venv\Scripts\python.exe main.py data\hustack\tc12.txt --algorithm my_solver
```

## Các Thuật Toán Hiện Có

```text
alns
round_robin
greedy_balanced
nearest_insertion
```

Chạy thử:

```powershell
.\.venv\Scripts\python.exe main.py data\hustack\tc12.txt --algorithm alns
```

Chạy so sánh nhiều thuật toán:

```powershell
.\.venv\Scripts\python.exe scripts\run_algorithm_benchmarks.py data\hustack --algorithms all --time-limit 5
```

## Ghi Chú Về Data

Các thư mục trong `data/` có file `HUONG_DAN.md` riêng để giải thích nguồn dữ
liệu, cách convert và reference. Trong toàn bộ project, `N` luôn là số bưu kiện.
