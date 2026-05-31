# MTSPLIB MinMax

This directory contains 16 Min-Max mTSP instances converted to the project
integer-matrix format:

- `eil51`: `K = 2, 3, 5, 7`
- `berlin52`: `K = 2, 3, 5, 7`
- `eil76`: `K = 2, 3, 5, 7`
- `rat99`: `K = 2, 3, 5, 7`

Raw source files live in `data/raw/mtsplib_minmax`.

Reference files:

- `reference.csv`: recommended reference for direct solver comparison. It is
  computed from the published MTSPLIB tour files and re-evaluated on the
  converted integer matrices in this directory.
- `reference_all.csv`: same computation, but includes extra starred long-run
  CPLEX tour files.

The published MTSPLIB tours start and end at the depot, so `reference.csv` uses
`return_to_depot = yes`. When comparing with these references, evaluate routes
with the return edge to depot included.

Regenerate:

```powershell
.\.venv\Scripts\python.exe scripts\install_report_benchmarks.py
.\.venv\Scripts\python.exe scripts\build_mtsplib_reference_from_tours.py
```
