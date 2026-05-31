# Raw MTSPLIB MinMax

Raw source for `data/mtsplib_minmax`.

- `tsp/`: original TSPLIB coordinate files for `eil51`, `berlin52`, `eil76`,
  and `rat99`.
- `tours/`: published MinMaxMTSP tour files downloaded from:

```text
https://profs.info.uaic.ro/mihaela.breaban/mtsplib/MinMaxMTSP/index.html
```

The old floating-point CPLEX table is stored as `reference_literature.csv` when
present. Direct solver comparison should use `data/mtsplib_minmax/reference.csv`,
which re-evaluates the published tours on the project's integer matrices.
