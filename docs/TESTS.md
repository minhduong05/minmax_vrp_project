# Tests

`tests/` chứa automated checks để bảo vệ các hành vi cơ bản của dự án.

Tests không thay thế benchmark chất lượng nghiệm. Chúng chỉ giúp trả lời các câu
hỏi:

- Parser có đọc đúng input format không?
- Objective `max_route`, `total_distance`, `balance` có tính đúng không?
- Solution có feasible không?
- 4 thuật toán đã đăng ký có trả về nghiệm feasible trên instance nhỏ không?
- Logic reference/gap/status trong benchmark có bị hỏng không?

## Cách Chạy

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Nếu báo lỗi `No module named pytest`, cài dev dependency trước:

```powershell
.\.venv\Scripts\python.exe -m pip install pytest
```

## Các File Test Hiện Có

```text
tests/test_io_models.py
tests/test_algorithms_smoke.py
tests/test_benchmark_helpers.py
```

## Khi Nào Nên Thêm Test

Nên thêm test khi:

- sửa `minmax_vrp/io.py`
- sửa `minmax_vrp/models.py`
- thêm thuật toán mới
- sửa `registry.py`
- sửa cách benchmark đọc reference hoặc tính gap
- sửa format output/summary

Một test tốt nên nhỏ, nhanh, và có expected value rõ ràng.
