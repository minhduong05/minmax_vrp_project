# Raw CVRPLIB

Raw `.vrp` files downloaded from CVRPLIB/Galgos:

```text
https://galgos.inf.puc-rio.br/cvrplib/en/instances
```

The converted project files keep only:

- coordinates or explicit distance data,
- depot position,
- selected vehicle count `K`.

Capacity, demand, and original CVRP best-known solutions are not used because
the current solver models Min-Max VRP without capacity constraints.
