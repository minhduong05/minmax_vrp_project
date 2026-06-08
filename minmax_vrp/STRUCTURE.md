# Cau truc thu muc `minmax_vrp`

Thu muc `minmax_vrp/` la package Python chua model du lieu, contract chung cho cac thuat toan va cac solver Min-Max VRP. Luong chay hien tai la:

1. `parser.py` o thu muc goc doc du lieu raw va tao `minmax_vrp.models.Instance`.
2. `run.py` o thu muc goc tao `AlgorithmConfig`, chon thuat toan qua registry.
3. Solver trong `minmax_vrp/algorithms/` nhan `Instance`, tra ve `AlgorithmResult`.
4. `run.py` in summary va co the ghi solution bang `minmax_vrp.io.write_solution`.

Bai toan hien tai dung route mo: moi tuyen bat dau tu depot `0`, di qua cac diem giao, va khong tinh quang duong quay ve depot.

## Cay thu muc

```text
minmax_vrp/
|-- __init__.py
|-- io.py
|-- models.py
|-- STRUCTURE.md
`-- algorithms/
    |-- __init__.py
    |-- base.py
    |-- registry.py
    |-- alns/
    |   |-- __init__.py
    |   |-- acceptance.py
    |   |-- adapter.py
    |   |-- adaptive.py
    |   |-- construction.py
    |   |-- destroy.py
    |   |-- operators_utils.py
    |   |-- repair.py
    |   `-- solver.py
    |-- tabu_search/
    |   |-- __init__.py
    |   |-- solver.py
    |   `-- tabu_search.py
    `-- vns/
        |-- __init__.py
        |-- solver.py
        `-- submit_vns.py
```

## File cap package

### `__init__.py`

Export cac thanh phan hay dung khi import package:

- `Instance`, `Solution`
- `AlgorithmConfig`, `ALGORITHM_NAMES`, `create_solver`
- `ALNSConfig`, `ALNSSolver`

File nay dung lazy import qua `__getattr__` de tranh import tat ca solver ngay khi import package.

### `models.py`

Dinh nghia du lieu loi cua bai toan:

- `Distance = float`: khoang cach duoc xu ly bang so thuc.
- `Instance`: gom `n`, `k`, va ma tran distance kich thuoc `(n + 1) x (n + 1)`.
- `Evaluation`: bo muc tieu `(max_route_length, balance, total_distance)`.
- `Solution`: danh sach routes, kiem tra feasible, tinh route length, tinh objective.
- `better()`: so sanh 2 solution theo objective lexicographic Min-Max.

Day la file quan trong nhat de cac thuat toan noi cung mot ngon ngu du lieu.

### `io.py`

Doc/ghi dinh dang input-output don gian cua project:

- `read_instance()`: doc input dang ma tran da convert san.
- `format_solution()`: chuyen `Solution` thanh output text.
- `write_solution()`: ghi solution ra file.
- `write_instance()`: ghi `Instance` ra file.
- `format_distance()`: giu so nguyen gon, nhung van bao toan khoang cach thuc.

Hien tai pipeline chinh dung `parser.py` o thu muc goc de doc raw data, nen `io.py` chu yeu dung cho output va dinh dang input noi bo neu can.

## `algorithms/`

Thu muc nay chua contract chung va cac thuat toan duoc giu lai: `alns`, `vns`, `tabu_search`.

### `algorithms/__init__.py`

Export API chung cua module algorithms:

- `AlgorithmConfig`
- `AlgorithmResult`
- `SolverAlgorithm`
- `ALGORITHM_NAMES`
- `create_solver`

### `algorithms/base.py`

Dinh nghia contract chung cho tat ca solver:

- `AlgorithmConfig`: cau hinh chung tu CLI, gom time limit, seed, local search cho Tabu, va tham so q theo ti le cho ALNS. Route mo la quy uoc co dinh cua project, khong con la config.
- `AlgorithmResult`: ket qua chuan hoa, gom best solution, ten thuat toan, runtime, iterations, objective va stats.
- `SolverAlgorithm`: base class bat buoc solver co method `solve(instance)`.

### `algorithms/registry.py`

Noi dang ky cac thuat toan duoc phep chay:

- `alns`
- `vns`
- `tabu_search`

`run.py` goi `create_solver(name, config)` tu file nay de tao solver dung theo CLI.

## `algorithms/alns/`

ALNS la Adaptive Large Neighborhood Search. Phan nay duoc tach thanh nhieu file nho vi thuat toan co nhieu thanh phan: construction, destroy, repair, acceptance va adaptive weights.

### `alns/__init__.py`

Export:

- `ALNSAlgorithm`: adapter theo contract chung.
- `ALNSConfig`, `ALNSResult`, `ALNSSolver`: solver ALNS goc.

### `alns/adapter.py`

Lop cau noi giua framework chung va ALNS goc.

`ALNSAlgorithm` nhan `AlgorithmConfig`, map sang `ALNSConfig`, goi `ALNSSolver`, roi dong goi ket qua thanh `AlgorithmResult`.

### `alns/solver.py`

Core ALNS:

- tao initial solution bang greedy balanced;
- lap destroy/repair den khi het time limit;
- dung simulated annealing de chap nhan nghiem;
- cap nhat trong so operator thich nghi.

### `alns/construction.py`

Tao solution ban dau:

- `build_round_robin()`: chia diem vong tron don gian.
- `build_greedy_balanced()`: chen diem theo huong can bang max route.

### `alns/destroy.py`

Cac destroy operator, tuc la chon mot tap diem de remove khoi solution hien tai. Vi du: random removal, worst-route removal, related removal.

### `alns/repair.py`

Cac repair operator, tuc la chen lai cac diem da remove vao route. Muc tieu la lam giam max route truoc, sau do den balance, roi den total distance.

### `alns/operators_utils.py`

Ham tien ich dung chung cho destroy/repair:

- tinh insertion delta;
- tinh removal saving;
- clone routes;
- thu thap pickup points.

### `alns/adaptive.py`

Quan ly trong so operator ALNS. Operator nao tao nghiem tot hon se duoc tang trong so, operator kem se giam dan theo `reaction`.

### `alns/acceptance.py`

Chien luoc chap nhan nghiem moi bang simulated annealing. Giup ALNS thoat local optimum thay vi chi nhan nghiem tot hon.

## `algorithms/tabu_search/`

Tabu Search cho Min-Max VRP.

### `tabu_search/__init__.py`

Export `TabuSearchAlgorithm`.

### `tabu_search/solver.py`

Adapter theo contract chung:

- nhan `AlgorithmConfig`;
- goi core `tabu_search()` voi deadline;
- neu bat `--local-search`, goi `local_clear()`;
- dong goi ket qua thanh `AlgorithmResult`.

### `tabu_search/tabu_search.py`

Core Tabu Search:

- tao initial solution bang greedy balanced insertion;
- sinh candidate tu route dai nhat bang relocate, swap, reverse;
- dung tabu list de tranh lap lai move;
- objective la `(max_route, balance, total_distance)`;
- tinh route theo bai toan mo, khong cong canh quay ve depot;
- doc input phu bang `float` neu chay standalone.

## `algorithms/vns/`

VNS la Variable Neighborhood Search.

### `vns/__init__.py`

Export `VNSAlgorithm`.

### `vns/solver.py`

Adapter theo contract chung:

- map `AlgorithmConfig.time_limit` va `seed` vao module VNS legacy;
- chay theo quy uoc route mo cua project;
- kiem tra feasible va dong goi `AlgorithmResult`.

### `vns/submit_vns.py`

Core VNS:

- tao initial solution bang greedy insertion;
- dung VND voi cac neighborhood relocate, swap, 2-opt;
- shake nghiem hien tai theo muc do `k`;
- so sanh bang objective sorted route lengths theo huong Min-Max;
- tinh route theo bai toan mo, khong cong canh quay ve depot;
- dam bao van tao nghiem feasible ngay ca khi time limit rat nho.

## Ket luan sau khi ra soat

- Khong can xoa them source file trong `minmax_vrp/`.
- Cac folder thuat toan con lai deu dang duoc registry dung.
- Da xoa cac folder `__pycache__/` vi day la cache sinh tu Python, khong phai source.
- `base.py`, `registry.py`, cac file `solver.py` va `__init__.py` la can thiet de `run.py` goi thuat toan thong nhat.
