# Data

This directory stores all benchmark data used by the project.

Project input format:

```text
N K
d[0][0] d[0][1] ... d[0][N]
...
d[N][0] d[N][1] ... d[N][N]
```

`N` is the number of customers, excluding depot `0`. `K` is the number of
routes/vehicles/salesmen. Every converted distance matrix in this project uses
integer distances.

Raw-to-converted rule:

- `EUC_2D`: `int(sqrt((x1-x2)^2 + (y1-y2)^2) + 0.5)`.
- `CEIL_2D`: `ceil(Euclidean distance)`.
- `ATT` and `GEO`: TSPLIB's standard formulas.
- `EXPLICIT`: use the integer matrix from the raw file.

Main scripts:

```powershell
.\.venv\Scripts\python.exe scripts\download_raw_benchmarks.py
.\.venv\Scripts\python.exe scripts\install_report_benchmarks.py
.\.venv\Scripts\python.exe scripts\build_mtsplib_reference_from_tours.py
.\.venv\Scripts\python.exe scripts\build_hustack_reference.py
.\.venv\Scripts\python.exe scripts\validate_data_pipeline.py
```

Reference files use `objective_max_route` as the primary objective. The
`total_distance` column is retained because the solver uses it as a tie-break
when two solutions have the same maximum route length.
