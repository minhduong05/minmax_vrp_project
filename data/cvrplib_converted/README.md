# CVRPLIB Converted

Selected CVRPLIB CVRP instances converted to the project integer-matrix input
format.

Raw source files live in `data/raw/cvrplib`. Regenerate with:

```powershell
.\.venv\Scripts\python.exe scripts\install_report_benchmarks.py
```

The conversion ignores demands, capacity, and CVRP best-known solutions. Those
belong to the original capacitated problem and are not direct references for the
current Min-Max objective.
