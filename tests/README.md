# Tests

Thư mục này chứa các kiểm tra tự động bằng `pytest` cho dự án.

Tests hữu ích khi bạn sửa solver, input parser, benchmark script, hoặc cách tính
objective. Mỗi test nên nhỏ, nhanh, và tập trung vào một hành vi cụ thể.

Chạy toàn bộ test:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Các nhóm test hiện có:

- `test_io_models.py`: input parsing, solution feasibility, route lengths, objective values.
- `test_algorithms_smoke.py`: mọi thuật toán đã đăng ký phải trả nghiệm feasible trên instance nhỏ.
- `test_benchmark_helpers.py`: benchmark reference matching, gap calculation, comparison status.
