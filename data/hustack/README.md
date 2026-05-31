# HUSTACK

HUSTACK input files are already in the project integer-matrix format.

- `tc*.txt`: input instances.
- `reference.csv`: jury solutions re-evaluated on the integer input matrices.
- `reference_jury.csv`: same content as `reference.csv`, kept for compatibility
  with earlier notes.

The HUSTACK objective does not include the return edge to depot, so
`return_to_depot = no` in the reference file.

Regenerate reference from raw jury outputs:

```powershell
.\.venv\Scripts\python.exe scripts\build_hustack_reference.py
```
