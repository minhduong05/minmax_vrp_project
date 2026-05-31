# Raw TSPLIB

Raw `.tsp` files downloaded from the TSPLIB GitHub mirror archive:

```text
https://github.com/mastqe/tsplib/archive/refs/heads/master.zip
```

Only the curated subset used by `data/tsplib_converted` and
`data/mtsplib_minmax` is kept here. Distances are integer matrices computed from
the raw `EDGE_WEIGHT_TYPE`.
For `EUC_2D`, the project uses the TSPLIB nearest-integer rule:

```text
int(sqrt(dx^2 + dy^2) + 0.5)
```
