# Giai Thich Cac Bo Generated Data

Trong `data/generated`, hien co **48 instance**, chia thanh **6 nhom**. Tat ca deu dung format:

```text
N K
distance matrix (N+1) x (N+1)
```

Node `0` la depot, node `1..N` la pickup. Vi bai toan hien tai la **route mo**, moi route bat dau tu depot nhung **khong quay ve depot**, nen vi tri depot va hinh dang phan bo diem anh huong rat manh toi objective.

## 1. `uniform`

Nhom baseline co ban nhat.

Pickup duoc phan bo deu trong hinh vuong `[0, 1000] x [0, 1000]`, depot o trung tam `(500, 500)`.

Co 9 file:

```text
n=100,  k=5,   seed01..03
n=300,  k=20,  seed01..03
n=1000, k=100, seed01..03
```

Dung de phan tich:

- Chat luong trung binh cua thuat toan khi du lieu khong co cau truc dac biet.
- Toc do mo rong khi tang `N`.
- Do on dinh theo seed.
- So sanh tong quat giua ALNS, VNS va Tabu.

Neu thuat toan chay kem tren `uniform`, thuong la dau hieu thuat toan nen chua on.

## 2. `cluster`

Nhom du lieu co cac cum pickup ro rang.

Depot o trung tam `(500, 500)`. Pickup duoc sinh quanh nhieu tam cum, co Gaussian noise.

Co 9 file:

```text
cluster5_n100_k5_seed01..03
cluster10_n300_k20_seed01..03
cluster20_n1000_k100_seed01..03
```

Dung de phan tich:

- Thuat toan co biet chia route theo cum khong.
- Destroy/repair cua ALNS co sua duoc route bi chia cum sai khong.
- VNS/Tabu co bi ket khi can chuyen nhieu diem giua cac cum khong.
- Kha nang can bang max-route khi cac cum khong deu.

Day la nhom rat quan trong cho Min-Max VRP, vi neu mot route om sai nhieu cum xa nhau thi `max_route` tang manh.

## 3. `outlier`

Nhom co phan lon pickup gan depot, nhung mot so diem nam rat xa o cac goc.

Depot o trung tam `(500, 500)`.

Co 9 file:

```text
outlier10pct_n100_k5_seed01..03
outlier10pct_n300_k20_seed01..03
outlier5pct_n1000_k100_seed01..03
```

Dung de phan tich:

- Thuat toan xu ly diem xa tot khong.
- Co phan tan outlier hop ly giua cac route khong.
- Co bi don nhieu outlier vao mot route lam `max_route` rat lon khong.
- Cac operator nhu worst-route removal, route removal co thuc su giup giam route dai nhat khong.

Nhom nay kiem tra dung ban chat Min-Max: chi vai diem xa co the quyet dinh toan bo objective chinh.

## 4. `corridor`

Nhom du lieu dang hanh lang/dai dai.

Depot o canh trai `(0, 500)`. Pickup nam gan mot duong ngang dai, `x` trai deu tu `0` toi `1000`, `y` dao dong nho quanh `500`.

Co 9 file:

```text
corridor_edge_n100_k5_seed01..03
corridor_edge_n300_k20_seed01..03
corridor_edge_n1000_k100_seed01..03
```

Dung de phan tich:

- Thuat toan co chia doan theo chieu dai hanh lang khong.
- Co tranh viec mot route di qua xa ve cuoi hanh lang khong.
- Route mo co duoc tan dung tot khong, vi khong can quay ve depot.
- Kha nang can bang route theo cau truc gan nhu mot chieu.

Nhom nay rat khac `uniform`: khoang cach chu yeu phu thuoc vao vi tri doc theo mot truc.

## 5. `k_sensitivity`

Nhom kiem tra tac dong cua so route/xe `K`.

Giu `N = 500`, thay doi `K`.

Co 6 file:

```text
uniform_center_n500_k2_seed01
uniform_center_n500_k10_seed01
uniform_center_n500_k50_seed01

cluster_n500_k2_seed01
cluster_n500_k10_seed01
cluster_n500_k50_seed01
```

Dung de phan tich:

- Khi `K` nho, moi route phai chua nhieu diem, `max_route` lon.
- Khi `K` lon, route ngan hon nhung thuat toan phai quan ly nhieu route hon.
- Thuat toan co scale tot theo so route khong.
- Co tao qua nhieu route rong/ngan khong.
- Balance thay doi the nao khi tang `K`.

Nhom nay dac biet huu ich de xem thuat toan nao nhay voi so xe.

## 6. `depot_position`

Nhom moi them de phan tich tac dong cua vi tri depot.

Giu cung pickup voi nhom `uniform` o cau hinh:

```text
N = 300
K = 20
seed01..03
```

Nhung doi vi tri depot.

Co 6 file:

```text
uniform_edge_n300_k20_seed01..03
uniform_corner_n300_k20_seed01..03
```

So sanh truc tiep voi:

```text
uniform/uniform_center_n300_k20_seed01..03
```

Tuc la cung pickup, chi khac depot:

```text
center: (500, 500)  trong nhom uniform
edge:   (0, 500)    trong nhom depot_position
corner: (0, 0)      trong nhom depot_position
```

Dung de phan tich:

- Route mo nhay the nao voi vi tri xuat phat.
- Thuat toan co con can bang tot khi depot lech tam khong.
- Khi depot o goc, cac diem xa phia doi dien co lam `max_route` tang manh khong.
- Thuat toan co chia route theo huong lan ra tu depot khong.

Nhom nay rat dang phan tich vi bai toan **khong quay ve depot**. Neu la route dong, depot o dau cung anh huong theo kieu khac; con route mo thi depot la diem xuat phat mot chieu, nen tac dong manh hon.

## Cach Dung Khi Phan Tich

Nen phan tich theo tung cau hoi:

```text
uniform         -> baseline tong quat
cluster         -> kha nang khai thac cau truc cum
outlier         -> kha nang xu ly diem xa
corridor        -> kha nang chia route theo hinh hoc mot chieu
k_sensitivity   -> do nhay voi so xe K
depot_position  -> do nhay voi vi tri depot trong route mo
```

Metric nen bao cao:

- `max_route`: objective chinh.
- `total_distance`: metric phu.
- `balance`: do lech giua route dai nhat va ngan nhat.
- `runtime`: thoi gian chay.
- `iterations`: so vong lap neu thuat toan co.
- `mean/std` neu chay nhieu seed thuat toan.

Neu lam bang so sanh thuat toan, nen tach theo nhom data, khong nen gop tat ca lai ngay tu dau, vi moi nhom kiem tra mot loai nang luc khac nhau cua thuat toan.
