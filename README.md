# Min-Max VRP

Project nay cai dat va so sanh cac heuristic cho bai toan Min-Max Vehicle
Routing Problem. Moi route la route mo: bat dau tu depot `0`, di qua cac diem
khach hang, va khong tinh canh quay ve depot.

Parser doc truc tiep du lieu TSPLIB, CVRPLIB hoac generated matrix vao
`Instance`; `run.py` chon solver qua registry va in nghiem tot nhat.

## Thanh phan chinh

```text
minmax_vrp/       package chinh: models, objective, solver registry, algorithms
parser.py         parser cho TSPLIB, CVRPLIB va generated matrix
run.py            CLI chay mot instance
scripts/          script sinh data, tuning va benchmark
tests/            unit/smoke tests
data/
  raw/            benchmark goc TSPLIB/CVRPLIB
  generated/      synthetic instances
  splits/         manifest dung cho tuning/test
```

Thu muc `output/` chi chua ket qua chay, tuning va report artifact. Thu muc nay
duoc ignore va khong can commit len GitHub.

## Cai dat

Yeu cau Python `3.11+`.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

Neu dung `uv`:

```powershell
uv sync --extra dev
```

## Chay solver

CVRPLIB thuong co so xe `k` trong ten file:

```powershell
.\.venv\Scripts\python.exe run.py data\raw\cvrplib\A-n32-k5.vrp --algorithm alns --time-limit 5
```

TSPLIB khong encode `k`, nen can truyen them:

```powershell
.\.venv\Scripts\python.exe run.py data\raw\tsplib\eil51.tsp --k 2 --algorithm alns --time-limit 5
```

Generated matrix da co san `N K` trong file:

```powershell
.\.venv\Scripts\python.exe run.py data\generated\uniform\uniform_center_n100_k5_seed01.txt --algorithm alns --time-limit 10
```

Ghi solution ra file:

```powershell
.\.venv\Scripts\python.exe run.py data\raw\cvrplib\A-n32-k5.vrp --algorithm alns -o solution.txt
```

## Thuat toan

Repo hien dang ky 3 solver:

- `alns`: Adaptive Large Neighborhood Search.
- `vns`: Variable Neighborhood Search.
- `tabu_search`: Tabu Search baseline.

Xem danh sach solver bang:

```powershell
.\.venv\Scripts\python.exe -c "from minmax_vrp.algorithms import ALGORITHM_NAMES; print(ALGORITHM_NAMES)"
```

## Data va benchmark

Sinh lai generated data:

```powershell
.\.venv\Scripts\python.exe scripts\generate_generated_data.py
```

Chay tuning/benchmark co the tao nhieu CSV/JSON trong `output/`. Day la artifact
cuc bo, khong nam trong source can commit.

Mot vai script huu ich:

- `scripts/tune_alns_configs.py`: tuning cau hinh ALNS.
- `scripts/tune_tabu_configs.py`: tuning Tabu Search.
- `scripts/test_best_algorithm.py`: chay cau hinh tot nhat tren split test.
- `scripts/compare_best_algorithm_results.py`: gom ket qua benchmark.

## Kiem tra

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Ghi chu truoc khi push

Nen commit cac file source, tests, data benchmark va README. Khong commit
`.venv/`, cache Python, `output/` hoac file solution/report sinh ra tu cac lan
chay thu nghiem.
