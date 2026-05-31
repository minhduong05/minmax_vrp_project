# TSPLIB Converted

Curated TSPLIB instances converted to the project integer-matrix input format.

Selected report files:

- `eil51_k2.txt`
- `berlin52_k3.txt`
- `kroA100_k5.txt`
- `ch130_k10.txt`
- `kroA200_k20.txt`
- `lin318_k20.txt`
- `pcb442_k50.txt`
- `u724_k100.txt`

Raw source files live in `data/raw/tsplib`. Regenerate with:

```powershell
.\.venv\Scripts\python.exe scripts\install_report_benchmarks.py
```

There is no direct reference file here because `K` is chosen by this project,
and no Min-Max route solution is provided by TSPLIB for these converted cases.
