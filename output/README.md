# Output experiments

Thu muc `output/` dung de luu lai ket qua thuc nghiem. Khong dat raw data o day; raw data nam trong `data/`.

## Cau truc

```text
output/
|-- README.md
|-- config_tuning/
|   |-- README.md
|   `-- .gitkeep
|-- algorithm_comparison/
|   |-- README.md
|   `-- .gitkeep
|-- convergence/
|   |-- README.md
|   `-- .gitkeep
`-- templates/
    |-- config_tuning.csv
    |-- algorithm_comparison.csv
    `-- convergence.csv
```

## 1. `config_tuning/`

Luu cac thuc nghiem chon config tot nhat cho tung thuat toan.

Muc tieu:

- Kiem tra moi config dua vao co tac dong thuc su den ket qua hay khong.
- Chon config tot nhat cho tung algorithm tren mot tap validation instances.
- Ghi lai config, seed, runtime, objective va route lengths.

Goi y dat ten file:

```text
output/config_tuning/2026-06-04_alns_eil51.csv
output/config_tuning/2026-06-04_vns_small_set.csv
```

## 2. `algorithm_comparison/`

Luu cac thuc nghiem so sanh cac thuat toan tren nhieu bo data.

Muc tieu:

- So sanh `alns`, `vns`, `tabu_search`, `ortools_routing`.
- Chay cung instance, cung `k`, cung time limit, nhieu seed neu thuat toan co random.
- Tong hop theo metric: best, mean, std, runtime, feasible rate.

Goi y dat ten file:

```text
output/algorithm_comparison/2026-06-04_tsplib_k2.csv
output/algorithm_comparison/2026-06-04_cvrplib_small.csv
```

## 3. `convergence/`

Luu metrics ve hoi tu theo iteration hoac thoi gian.

Muc tieu:

- Theo doi objective thay doi qua iteration/time.
- Ve bieu do convergence curve.
- So sanh toc do hoi tu cua cac algorithm.

Goi y dat ten file:

```text
output/convergence/2026-06-04_alns_eil51_seed7.csv
output/convergence/2026-06-04_tabu_eil51_seed7.csv
```

## Metric nen luu chung

- `timestamp`
- `experiment_type`
- `algorithm`
- `instance`
- `n`
- `k`
- `seed`
- `time_limit`
- `return_to_depot`
- `feasible`
- `max_route`
- `total_distance`
- `balance`
- `runtime`
- `iterations`
- `config`
- `notes`

## Quy uoc

- Dung CSV cho bang tong hop.
- Dung JSON neu can luu config phuc tap.
- Dung `.txt` cho route solution neu can doi chieu.
- Moi thuc nghiem nen co ngay chay trong ten file.
