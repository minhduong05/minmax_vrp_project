# Min-Max VRP

Repo này chạy bài toán Min-Max VRP trực tiếp từ dữ liệu raw. Parser đọc dữ liệu
vào bộ nhớ, tạo `Instance`, rồi `run.py` truyền thẳng cho thuật toán. Không còn
bước convert raw thành input trung gian.

## Cấu Trúc Chính

```text
data/
  raw/          dữ liệu gốc: TSPLIB .tsp, CVRPLIB .vrp, MTSPLIB raw files
  generated/    dữ liệu sẽ sinh bằng tọa độ sau này

parser.py       đọc raw/generated input và trả Instance trong RAM
run.py          CLI chạy 1 instance với cấu hình thuật toán
minmax_vrp/     model, objective, thuật toán
```

Mặc định mọi route được tính đóng vòng: `0 -> ... -> 0`.

## Chạy

CVRPLIB thường có `k` trong tên file, ví dụ `A-n32-k5.vrp`, nên có thể chạy:

```powershell
.\.venv\Scripts\python.exe run.py data\raw\cvrplib\A-n32-k5.vrp --algorithm alns --time-limit 5
```

TSPLIB/MTSPLIB raw không có `k` trong file, nên truyền thêm:

```powershell
.\.venv\Scripts\python.exe run.py data\raw\tsplib\eil51.tsp --k 2 --algorithm alns --time-limit 5
```

Nếu muốn route mở, không quay về depot:

```powershell
.\.venv\Scripts\python.exe run.py data\raw\tsplib\eil51.tsp --k 2 --no-return-to-depot
```

Ghi solution ra file tùy chọn:

```powershell
.\.venv\Scripts\python.exe run.py data\raw\cvrplib\A-n32-k5.vrp -o solution.txt
```

## Thuật Toán

Xem danh sách thuật toán hiện có:

```powershell
.\.venv\Scripts\python.exe -c "from minmax_vrp.algorithms import ALGORITHM_NAMES; print(ALGORITHM_NAMES)"
```

Hiện repo đăng ký các thuật toán còn tồn tại trong `minmax_vrp/algorithms/`.
