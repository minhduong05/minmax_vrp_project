# Raw Data

Raw source files are kept here so the conversion pipeline is reproducible.

- `tsplib/`: downloaded `.tsp` files from the TSPLIB mirror archive used by the
  scripts.
- `cvrplib/`: selected `.vrp` files downloaded from CVRPLIB/Galgos.
- `mtsplib_minmax/`: source `.tsp` files and published MinMaxMTSP tour files.
- `hustack_jury/`: jury output files copied from HUSTACK.

Converted files are generated from this directory by:

```powershell
.\.venv\Scripts\python.exe scripts\install_report_benchmarks.py
```
