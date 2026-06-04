# Generated Data

Thu muc nay chua cac instance synthetic cho bai toan Min-Max VRP. Tat ca file
`.txt` dung cung format noi bo cua project:

```text
N K
distance_matrix_row_0
distance_matrix_row_1
...
distance_matrix_row_N
```

Trong do:

- `N` la so diem pickup, khong tinh depot.
- `K` la so route/xe.
- Node `0` la depot.
- Node `1..N` la cac diem pickup.
- Ma tran co kich thuoc `(N + 1) x (N + 1)`.
- Cac instance Euclidean dung khoang cach thuc, khong lam tron ve so nguyen.

Lenh sinh lai toan bo bo data:

```powershell
.\.venv\Scripts\python.exe scripts\generate_generated_data.py
```

Lenh chay thu mot instance:

```powershell
.\.venv\Scripts\python.exe run.py data\generated\uniform\uniform_center_n100_k5_seed01.txt --algorithm alns --time-limit 10
```

## Tong quan

Bo generated data gom 48 file, chia thanh 6 nhom:

| Nhom | So file | Muc dich |
|---|---:|---|
| `uniform` | 9 | Baseline trung lap, cac diem phan bo deu trong mat phang. |
| `cluster` | 9 | Kiem tra kha nang chia cum va sua nghiem phan vung sai. |
| `outlier` | 9 | Kiem tra kha nang xu ly diem xa, rat quan trong voi objective min-max. |
| `corridor` | 9 | Kiem tra du lieu dang hanh lang/duong dai, depot o dau hanh lang. |
| `asymmetric` | 6 | Kiem tra code voi ma tran bat doi xung. |
| `k_sensitivity` | 6 | Kiem tra anh huong cua so xe `K` khi giu `N = 500`. |

## Tham so sinh chung

| Tham so | Gia tri |
|---|---|
| Khong gian toa do | `[0, 1000] x [0, 1000]` |
| Depot trung tam | `(500, 500)` |
| Depot corridor | `(0, 500)` |
| Khoang cach chinh | Euclidean distance |
| Seed chinh | `seed01`, `seed02`, `seed03` |
| File generator | `scripts/generate_generated_data.py` |

## Uniform

Nhom `uniform` la baseline trung lap. Depot nam o giua ban do tai `(500, 500)`,
cac diem pickup duoc sinh deu trong hinh vuong `[0, 1000] x [0, 1000]`.

Nhom nay dung de do toc do, chat luong trung binh, va anh huong cua kich thuoc
`N, K` trong truong hop khong co cau truc kho.

| File | N | K | Seed | Mo ta |
|---|---:|---:|---:|---|
| `uniform/uniform_center_n100_k5_seed01.txt` | 100 | 5 | 1 | Baseline nho, chay nhanh de debug va so sanh chat luong ban dau. |
| `uniform/uniform_center_n100_k5_seed02.txt` | 100 | 5 | 2 | Lap lai cung cau hinh nho voi seed khac de do do on dinh. |
| `uniform/uniform_center_n100_k5_seed03.txt` | 100 | 5 | 3 | Lap lai cung cau hinh nho voi seed khac de tinh mean/std. |
| `uniform/uniform_center_n300_k20_seed01.txt` | 300 | 20 | 1 | Baseline trung binh, phu hop so sanh hoi tu giua cac thuat toan. |
| `uniform/uniform_center_n300_k20_seed02.txt` | 300 | 20 | 2 | Lap lai cau hinh trung binh voi seed khac. |
| `uniform/uniform_center_n300_k20_seed03.txt` | 300 | 20 | 3 | Lap lai cau hinh trung binh voi seed khac. |
| `uniform/uniform_center_n1000_k100_seed01.txt` | 1000 | 100 | 1 | Stress test lon, kiem tra kha nang mo rong. |
| `uniform/uniform_center_n1000_k100_seed02.txt` | 1000 | 100 | 2 | Stress test lon voi seed khac. |
| `uniform/uniform_center_n1000_k100_seed03.txt` | 1000 | 100 | 3 | Stress test lon voi seed khac. |

## Cluster

Nhom `cluster` tao cac cum pickup cach nhau. Depot nam o trung tam `(500, 500)`.
Diem pickup duoc gan vao cac tam cum, sau do cong Gaussian noise.

Nhom nay dung de kiem tra kha nang chia cum cho cac route. Neu route nhan sai
cum, max-route co the tang manh. Nhom nay rat huu ich khi danh gia related
removal, route removal, va cac buoc repair cua ALNS.

| File | N | K | Seed | Mo ta |
|---|---:|---:|---:|---|
| `cluster/cluster5_n100_k5_seed01.txt` | 100 | 5 | 1 | 5 cum, kich thuoc nho, moi xe ly tuong co the phu trach mot phan cum. |
| `cluster/cluster5_n100_k5_seed02.txt` | 100 | 5 | 2 | 5 cum voi seed khac, dung de do do on dinh. |
| `cluster/cluster5_n100_k5_seed03.txt` | 100 | 5 | 3 | 5 cum voi seed khac, dung de tinh mean/std. |
| `cluster/cluster10_n300_k20_seed01.txt` | 300 | 20 | 1 | 10 cum, kich thuoc trung binh, route co the can chia cum linh hoat. |
| `cluster/cluster10_n300_k20_seed02.txt` | 300 | 20 | 2 | 10 cum voi seed khac. |
| `cluster/cluster10_n300_k20_seed03.txt` | 300 | 20 | 3 | 10 cum voi seed khac. |
| `cluster/cluster20_n1000_k100_seed01.txt` | 1000 | 100 | 1 | 20 cum, stress test kha nang mo rong va chia cum. |
| `cluster/cluster20_n1000_k100_seed02.txt` | 1000 | 100 | 2 | 20 cum voi seed khac. |
| `cluster/cluster20_n1000_k100_seed03.txt` | 1000 | 100 | 3 | 20 cum voi seed khac. |

## Outlier

Nhom `outlier` tao phan lon diem gan depot, nhung mot ty le nho diem nam rat
xa o cac goc ban do. Depot nam o trung tam `(500, 500)`.

Day la nhom quan trong cho Min-Max VRP vi mot vai diem xa co the quyet dinh
gia tri `max_route`. Thuat toan tot can phan tan cac diem xa hop ly thay vi
don nhieu diem xa vao cung mot route.

| File | N | K | Seed | Mo ta |
|---|---:|---:|---:|---|
| `outlier/outlier10pct_n100_k5_seed01.txt` | 100 | 5 | 1 | 10% diem xa, kich thuoc nho, de thay tac dong cua diem outlier. |
| `outlier/outlier10pct_n100_k5_seed02.txt` | 100 | 5 | 2 | 10% diem xa voi seed khac. |
| `outlier/outlier10pct_n100_k5_seed03.txt` | 100 | 5 | 3 | 10% diem xa voi seed khac. |
| `outlier/outlier10pct_n300_k20_seed01.txt` | 300 | 20 | 1 | 10% diem xa, kich thuoc trung binh. |
| `outlier/outlier10pct_n300_k20_seed02.txt` | 300 | 20 | 2 | 10% diem xa voi seed khac. |
| `outlier/outlier10pct_n300_k20_seed03.txt` | 300 | 20 | 3 | 10% diem xa voi seed khac. |
| `outlier/outlier5pct_n1000_k100_seed01.txt` | 1000 | 100 | 1 | 5% diem xa, stress test lon cho kha nang can bang max-route. |
| `outlier/outlier5pct_n1000_k100_seed02.txt` | 1000 | 100 | 2 | 5% diem xa voi seed khac. |
| `outlier/outlier5pct_n1000_k100_seed03.txt` | 1000 | 100 | 3 | 5% diem xa voi seed khac. |

## Corridor

Nhom `corridor` tao cac diem gan mot duong ngang dai. Depot nam o dau hanh lang
tai `(0, 500)`. Pickup co `x` trai deu trong `[0, 1000]`, con `y` dao dong nho
quanh `500`.

Nhom nay mo phong bai toan giao hang doc mot tuyen duong dai. Viec chia route
can can than vi mot xe di qua xa ve cuoi hanh lang se lam objective xau.

| File | N | K | Seed | Mo ta |
|---|---:|---:|---:|---|
| `corridor/corridor_edge_n100_k5_seed01.txt` | 100 | 5 | 1 | Hanh lang nho, depot o dau tuyen, dung de kiem tra chia doan. |
| `corridor/corridor_edge_n100_k5_seed02.txt` | 100 | 5 | 2 | Hanh lang nho voi seed khac. |
| `corridor/corridor_edge_n100_k5_seed03.txt` | 100 | 5 | 3 | Hanh lang nho voi seed khac. |
| `corridor/corridor_edge_n300_k20_seed01.txt` | 300 | 20 | 1 | Hanh lang trung binh, kiem tra can bang route theo mot huong. |
| `corridor/corridor_edge_n300_k20_seed02.txt` | 300 | 20 | 2 | Hanh lang trung binh voi seed khac. |
| `corridor/corridor_edge_n300_k20_seed03.txt` | 300 | 20 | 3 | Hanh lang trung binh voi seed khac. |
| `corridor/corridor_edge_n1000_k100_seed01.txt` | 1000 | 100 | 1 | Hanh lang lon, stress test cho cau truc gan nhu 1 chieu. |
| `corridor/corridor_edge_n1000_k100_seed02.txt` | 1000 | 100 | 2 | Hanh lang lon voi seed khac. |
| `corridor/corridor_edge_n1000_k100_seed03.txt` | 1000 | 100 | 3 | Hanh lang lon voi seed khac. |

## Asymmetric

Nhom `asymmetric` dung ma tran khoang cach bat doi xung, tuc la co the co
`d(i, j) != d(j, i)`. Toa do pickup ban dau van sinh uniform, depot nam o
trung tam `(500, 500)`, nhung khoang cach duoc nhan bias theo huong di.

Trong generator hien tai:

- Di ve huong dong/nam re hon.
- Di ve huong tay/bac dat hon.
- Duong cheo `d(i, i)` bang `0`.

Nhom nay dung de kiem tra xem thuat toan co ngam gia su ma tran doi xung hay
khong. Nen bao cao rieng voi nhom Euclidean chinh.

| File | N | K | Seed | Mo ta |
|---|---:|---:|---:|---|
| `asymmetric/asymmetric_n300_k50_seed01.txt` | 300 | 50 | 1 | Ma tran bat doi xung kich thuoc trung binh. |
| `asymmetric/asymmetric_n300_k50_seed02.txt` | 300 | 50 | 2 | Ma tran bat doi xung trung binh voi seed khac. |
| `asymmetric/asymmetric_n300_k50_seed03.txt` | 300 | 50 | 3 | Ma tran bat doi xung trung binh voi seed khac. |
| `asymmetric/asymmetric_n1000_k100_seed01.txt` | 1000 | 100 | 1 | Ma tran bat doi xung lon, stress test robustness. |
| `asymmetric/asymmetric_n1000_k100_seed02.txt` | 1000 | 100 | 2 | Ma tran bat doi xung lon voi seed khac. |
| `asymmetric/asymmetric_n1000_k100_seed03.txt` | 1000 | 100 | 3 | Ma tran bat doi xung lon voi seed khac. |

## K Sensitivity

Nhom `k_sensitivity` giu `N = 500`, thay doi `K` de xem so xe anh huong the
nao den max-route, balance, runtime, va kha nang hoi tu.

Co hai dang phan bo:

- `uniform_center`: pickup uniform, depot trung tam.
- `cluster`: pickup gom 10 cum, depot trung tam.

| File | N | K | Seed | Mo ta |
|---|---:|---:|---:|---|
| `k_sensitivity/uniform_center_n500_k2_seed01.txt` | 500 | 2 | 1 | Uniform voi rat it xe, route dai va kho can bang. |
| `k_sensitivity/uniform_center_n500_k10_seed01.txt` | 500 | 10 | 1 | Uniform voi so xe vua phai, cau hinh trung gian. |
| `k_sensitivity/uniform_center_n500_k50_seed01.txt` | 500 | 50 | 1 | Uniform voi nhieu xe, moi route ngan hon nhung can quan ly nhieu route. |
| `k_sensitivity/cluster_n500_k2_seed01.txt` | 500 | 2 | 1 | Cluster voi rat it xe, buoc chia cum rat kho. |
| `k_sensitivity/cluster_n500_k10_seed01.txt` | 500 | 10 | 1 | Cluster voi so xe vua phai, phu hop so sanh voi 10 cum. |
| `k_sensitivity/cluster_n500_k50_seed01.txt` | 500 | 50 | 1 | Cluster voi nhieu xe, kiem tra viec tach cum thanh nhieu route. |

## Metric nen bao cao

Khi chay thuat toan tren bo data nay, nen ghi lai cac metric sau:

| Metric | Y nghia |
|---|---|
| `max_route` | Objective chinh cua Min-Max VRP. |
| `total_distance` | Tong quang duong, dung lam metric phu. |
| `balance` | Do lech giua route dai nhat va ngan nhat. |
| `runtime` | Thoi gian chay. |
| `iterations` | So vong lap, neu solver co bao cao. |
| `best`, `mean`, `std` | Nen tinh khi chay nhieu seed thuat toan. |

Goi y doc ket qua theo tung nhom:

| Nhom | Dieu can quan sat |
|---|---|
| `uniform` | Toc do va chat luong trung binh. |
| `cluster` | Kha nang sua route bi chia cum sai. |
| `outlier` | Kha nang phan tan diem xa de giam max-route. |
| `corridor` | Kha nang chia doan theo huong tu depot ra xa. |
| `asymmetric` | Robustness khi `d(i, j)` khac `d(j, i)`. |
| `k_sensitivity` | Anh huong cua so xe `K` den objective va balance. |
