# Scripts

These scripts define the reproducible data pipeline used by the project.

Run the full pipeline:

```powershell
.\.venv\Scripts\python.exe scripts\download_raw_benchmarks.py
.\.venv\Scripts\python.exe scripts\install_report_benchmarks.py
.\.venv\Scripts\python.exe scripts\build_mtsplib_reference_from_tours.py
.\.venv\Scripts\python.exe scripts\build_hustack_reference.py
.\.venv\Scripts\python.exe scripts\validate_data_pipeline.py
```

Files kept:

- `benchmark_data_utils.py`: shared TSPLIB/CVRPLIB parser, depot remapping, and
  integer distance conversion helpers. `EUC_2D` uses
  `int(sqrt(dx^2 + dy^2) + 0.5)`.
- `download_raw_benchmarks.py`: downloads the raw data actually used by the
  project into `data/raw`.
- `install_report_benchmarks.py`: converts raw TSPLIB, CVRPLIB, and MTSPLIB
  files into project `.txt` integer-matrix inputs.
- `build_mtsplib_reference_from_tours.py`: rebuilds `data/mtsplib_minmax`
  references from published MTSPLIB tour files, evaluated on integer matrices.
- `build_hustack_reference.py`: rebuilds `data/hustack/reference.csv` from jury
  outputs in `data/raw/hustack_jury`.
- `validate_data_pipeline.py`: verifies converted matrices match raw sources and
  reference files have the expected integer schema.
- `run_algorithm_benchmarks.py`: runs one or more solver algorithms on benchmark
  files/directories and writes a comparison CSV.

Removed/ignored:

- `__pycache__/`: Python bytecode cache.
- Legacy one-off installers are removed so there is a single clear pipeline.
