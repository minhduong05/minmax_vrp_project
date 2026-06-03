# Hướng Dẫn Data

`data/` chứa toàn bộ dữ liệu dùng để chạy và so sánh thuật toán.

Quy ước input chuẩn:

```text
N K
d[0][0] d[0][1] ... d[0][N]
...
d[N][0] d[N][1] ... d[N][N]
```

Trong đó:

- `N`: số bưu kiện, không tính depot.
- `K`: số route/bưu tá/xe.
- Node `0`: depot.
- Node `1..N`: bưu kiện.
- Ma trận khoảng cách sau convert luôn là số nguyên.

Các nhóm dữ liệu:

```text
raw/                 dữ liệu gốc
hustack/             input HUSTACK + reference jury
mtsplib_minmax/      16 instance Min-Max mTSP + reference
tsplib_converted/    8 instance TSPLIB đã convert
cvrplib_converted/   9 instance CVRPLIB đã convert
generated/           để dành cho dữ liệu tự sinh
```

Pipeline tạo lại dữ liệu:

```powershell
.\.venv\Scripts\python.exe scripts\download_raw_benchmarks.py
.\.venv\Scripts\python.exe scripts\install_report_benchmarks.py
.\.venv\Scripts\python.exe scripts\build_mtsplib_reference_from_tours.py
.\.venv\Scripts\python.exe scripts\build_hustack_reference.py
.\.venv\Scripts\python.exe scripts\validate_data_pipeline.py
```
