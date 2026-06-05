# Min-Max VRP

Repo nay chay bai toan Min-Max VRP truc tiep tu du lieu raw hoac generated.
Moi route la route mo: bat dau tu depot `0`, di qua cac diem pickup, va khong
tinh canh quay ve depot.

Parser doc du lieu vao bo nho, tao `Instance`, roi `run.py` truyen thang cho
thuat toan. Khong con buoc convert raw thanh input trung gian.

## Cau Truc Chinh

```text
data/
  raw/          du lieu goc: TSPLIB .tsp, CVRPLIB .vrp
  generated/    du lieu ma tran tong hop de thuc nghiem

parser.py       doc raw/generated input va tra Instance trong RAM
run.py          CLI chay 1 instance voi cau hinh thuat toan
minmax_vrp/     model, objective, thuat toan
```

## Chay

CVRPLIB thuong co `k` trong ten file, vi du `A-n32-k5.vrp`, nen co the chay:

```powershell
.\.venv\Scripts\python.exe run.py data\raw\cvrplib\A-n32-k5.vrp --algorithm alns --time-limit 5
```

TSPLIB raw khong co `k` trong file, nen truyen them:

```powershell
.\.venv\Scripts\python.exe run.py data\raw\tsplib\eil51.tsp --k 2 --algorithm alns --time-limit 5
```

Generated matrix da co san `N K` trong file:

```powershell
.\.venv\Scripts\python.exe run.py data\generated\uniform\uniform_center_n100_k5_seed01.txt --algorithm alns --time-limit 10
```

Ghi solution ra file tuy chon:

```powershell
.\.venv\Scripts\python.exe run.py data\raw\cvrplib\A-n32-k5.vrp -o solution.txt
```

## Thuat Toan

Xem danh sach thuat toan hien co:

```powershell
.\.venv\Scripts\python.exe -c "from minmax_vrp.algorithms import ALGORITHM_NAMES; print(ALGORITHM_NAMES)"
```

Hien repo dang ky cac thuat toan con ton tai trong `minmax_vrp/algorithms/`.
