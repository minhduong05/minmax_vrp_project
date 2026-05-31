# Raw HUSTACK Jury Outputs

These `.out` files are the jury solutions copied from HUSTACK, one per input
file in `data/hustack`.

They use the same route-output format as the problem statement:

```text
K
route_length_1
0 ...
route_length_2
0 ...
...
```

`scripts/build_hustack_reference.py` validates customer coverage and computes
the integer objective values in `data/hustack/reference.csv`.
