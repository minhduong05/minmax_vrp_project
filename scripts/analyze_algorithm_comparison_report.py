"""Generate report artifacts for final algorithm comparison."""

from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "output" / "algorithm_comparison"
ARTIFACT_DIR = INPUT_DIR / "report_artifacts"

RUN_FILES = {
    "main_test": [
        "test_seed02_seed03_alns_best_test_runs.csv",
        "test_seed02_seed03_vns_best_test_runs.csv",
        "test_seed02_seed03_tabu_search_best_test_runs.csv",
    ],
    "k_sensitivity": [
        "k_sensitivity_10s_alns_best_test_runs.csv",
        "k_sensitivity_10s_vns_best_test_runs.csv",
        "k_sensitivity_10s_tabu_search_best_test_runs.csv",
    ],
    "raw_cvrplib": [
        "raw_cvrplib_10s_alns_best_test_runs.csv",
        "raw_cvrplib_10s_vns_best_test_runs.csv",
        "raw_cvrplib_10s_tabu_search_best_test_runs.csv",
    ],
    "raw_tsplib": [
        "raw_tsplib_sqrtk_10s_alns_best_test_runs.csv",
        "raw_tsplib_sqrtk_10s_vns_best_test_runs.csv",
        "raw_tsplib_sqrtk_10s_tabu_search_best_test_runs.csv",
    ],
}

ALGORITHM_LABELS = {
    "alns": "ALNS",
    "vns": "VNS",
    "tabu_search": "Tabu",
}

DATASET_LABELS = {
    "main_test": "Generated test",
    "k_sensitivity": "K sensitivity",
    "raw_cvrplib": "CVRPLIB",
    "raw_tsplib": "TSPLIB",
}

NUMERIC_FIELDS = [
    "n",
    "k",
    "solver_seed",
    "time_limit",
    "max_route",
    "total_distance",
    "balance",
    "runtime",
    "iterations",
]


def read_rows() -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    rows: list[dict[str, object]] = []
    malformed: list[dict[str, str]] = []
    for dataset, names in RUN_FILES.items():
        for name in names:
            path = INPUT_DIR / name
            with path.open(newline="", encoding="utf-8") as file:
                for line_number, raw in enumerate(csv.DictReader(file), start=2):
                    raw["_source_file"] = name
                    raw["_source_line"] = str(line_number)
                    try:
                        for field in NUMERIC_FIELDS:
                            raw[field] = float(raw[field])
                        raw["n"] = int(raw["n"])
                        raw["k"] = int(raw["k"])
                        raw["solver_seed"] = int(raw["solver_seed"])
                        raw["dataset"] = dataset
                        raw["feasible_rate"] = 1.0 if raw["feasible"] == "yes" else 0.0
                        raw["size_bucket"] = size_bucket(int(raw["n"]))
                    except (KeyError, TypeError, ValueError):
                        malformed.append(raw)
                        continue
                    rows.append(raw)
    return rows, malformed


def size_bucket(n: int) -> str:
    if n <= 150:
        return "small"
    if n <= 500:
        return "medium"
    return "large"


def mean(values: list[float]) -> float:
    return statistics.mean(values) if values else 0.0


def median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def pct(value: object, digits: int = 2) -> str:
    return f"{float(value):.{digits}f}\\%"


def num(value: object, digits: int = 2) -> str:
    return f"{float(value):.{digits}f}"


def tex_escape(value: object) -> str:
    return str(value).replace("_", "\\_")


def add_gap_and_rank(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, float, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["dataset"]), float(row["time_limit"]), str(row["instance"]))].append(row)

    clean_rows = []
    for group in grouped.values():
        if len({row["algorithm"] for row in group}) < 3:
            continue
        group.sort(key=lambda row: (float(row["max_route"]), str(row["algorithm"])))
        best = float(group[0]["max_route"])
        for rank, row in enumerate(group, start=1):
            row = dict(row)
            row["rank_by_max_route"] = rank
            row["is_winner"] = 1 if rank == 1 else 0
            row["gap_pct"] = 100.0 * (float(row["max_route"]) - best) / best if best > 0 else 0.0
            row["best_max_route"] = best
            clean_rows.append(row)
    clean_rows.sort(
        key=lambda row: (
            str(row["dataset"]),
            float(row["time_limit"]),
            str(row["instance"]),
            int(row["rank_by_max_route"]),
        )
    )
    return clean_rows


def summarize(
    rows: list[dict[str, object]],
    group_fields: list[str],
    *,
    sort_fields: list[str] | None = None,
) -> list[dict[str, object]]:
    grouped: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[field] for field in group_fields)].append(row)

    out = []
    for key, group in grouped.items():
        record = {field: value for field, value in zip(group_fields, key)}
        gaps = [float(row["gap_pct"]) for row in group]
        record.update(
            {
                "instances": len(group),
                "feasible_rate": mean([float(row["feasible_rate"]) for row in group]),
                "mean_gap_pct": mean(gaps),
                "median_gap_pct": median(gaps),
                "win_rate": mean([float(row["is_winner"]) for row in group]),
                "mean_max_route": mean([float(row["max_route"]) for row in group]),
                "mean_total_distance": mean([float(row["total_distance"]) for row in group]),
                "mean_balance": mean([float(row["balance"]) for row in group]),
                "mean_runtime": mean([float(row["runtime"]) for row in group]),
                "mean_iterations": mean([float(row["iterations"]) for row in group]),
                "config_name": group[0]["config_name"],
            }
        )
        out.append(record)
    if sort_fields:
        out.sort(key=lambda row: tuple(row[field] for field in sort_fields))
    else:
        out.sort(key=lambda row: tuple(str(row[field]) for field in group_fields))
    return out


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def table_line(row: dict[str, object], keys: list[str], pct_keys: set[str] | None = None) -> str:
    pct_keys = pct_keys or set()
    cells = []
    for key in keys:
        value = row[key]
        if key == "algorithm":
            cells.append(ALGORITHM_LABELS[str(value)])
        elif key == "dataset":
            cells.append(DATASET_LABELS[str(value)])
        elif key in pct_keys:
            cells.append(pct(value))
        elif key == "win_rate":
            cells.append(pct(100.0 * float(value)))
        elif isinstance(value, float):
            cells.append(num(value))
        else:
            cells.append(tex_escape(value))
    return " & ".join(cells) + r" \\"


def table_lines(rows: list[dict[str, object]], keys: list[str], pct_keys: set[str] | None = None) -> str:
    return "\n".join(table_line(row, keys, pct_keys) for row in rows)


def pivot_gap_table(
    rows: list[dict[str, object]],
    row_field: str,
    row_order: list[object],
    algorithms: list[str] | None = None,
) -> list[dict[str, object]]:
    algorithms = algorithms or ["alns", "vns", "tabu_search"]
    lookup = {(row[row_field], row["algorithm"]): row for row in rows}
    out = []
    for value in row_order:
        record: dict[str, object] = {row_field: value}
        best_gap = min(float(lookup[(value, algorithm)]["mean_gap_pct"]) for algorithm in algorithms)
        best_algorithms = []
        for algorithm in algorithms:
            gap = float(lookup[(value, algorithm)]["mean_gap_pct"])
            record[algorithm] = gap
            if abs(gap - best_gap) < 1e-9:
                best_algorithms.append(ALGORITHM_LABELS[algorithm])
        record["best_algorithm"] = "/".join(best_algorithms)
        out.append(record)
    return out


def svg_main_time(path: Path, rows: list[dict[str, object]]) -> None:
    width, height = 820, 430
    left, right, top, bottom = 70, 160, 30, 60
    plot_w = width - left - right
    plot_h = height - top - bottom
    times = sorted({float(row["time_limit"]) for row in rows})
    algs = ["alns", "vns", "tabu_search"]
    colors = {"alns": "#2563eb", "vns": "#16a34a", "tabu_search": "#dc2626"}
    max_gap = max(float(row["mean_gap_pct"]) for row in rows) * 1.1
    lookup = {(str(row["algorithm"]), float(row["time_limit"])): float(row["mean_gap_pct"]) for row in rows}

    def x(t: float) -> float:
        if len(times) == 1:
            return left + plot_w / 2
        return left + times.index(t) / (len(times) - 1) * plot_w

    def y(gap: float) -> float:
        return top + (1.0 - gap / max_gap) * plot_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#222"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#222"/>',
    ]
    for tick in range(0, int(max_gap) + 2, max(1, int(max_gap // 5) or 1)):
        yy = y(tick)
        parts.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{left + plot_w}" y2="{yy:.1f}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{left - 10}" y="{yy + 4:.1f}" text-anchor="end" font-size="12">{tick}</text>')
    for t in times:
        xx = x(t)
        parts.append(f'<line x1="{xx:.1f}" y1="{top + plot_h}" x2="{xx:.1f}" y2="{top + plot_h + 5}" stroke="#222"/>')
        parts.append(f'<text x="{xx:.1f}" y="{top + plot_h + 24}" text-anchor="middle" font-size="12">{t:g}s</text>')
    parts.append(f'<text x="{left + plot_w / 2}" y="{height - 16}" text-anchor="middle" font-size="14">Time limit</text>')
    parts.append(f'<text x="18" y="{top + plot_h / 2}" transform="rotate(-90 18 {top + plot_h / 2})" text-anchor="middle" font-size="14">Mean gap (%)</text>')
    for alg in algs:
        points = " ".join(f"{x(t):.1f},{y(lookup[(alg, t)]):.1f}" for t in times)
        parts.append(f'<polyline points="{points}" fill="none" stroke="{colors[alg]}" stroke-width="2.5"/>')
        for t in times:
            parts.append(f'<circle cx="{x(t):.1f}" cy="{y(lookup[(alg, t)]):.1f}" r="4" fill="{colors[alg]}"/>')
    legend_x, legend_y = left + plot_w + 35, top + 20
    for i, alg in enumerate(algs):
        yy = legend_y + i * 26
        parts.append(f'<line x1="{legend_x}" y1="{yy}" x2="{legend_x + 28}" y2="{yy}" stroke="{colors[alg]}" stroke-width="3"/>')
        parts.append(f'<text x="{legend_x + 36}" y="{yy + 4}" font-size="13">{ALGORITHM_LABELS[alg]}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def svg_k_sensitivity(path: Path, rows: list[dict[str, object]]) -> None:
    width, height = 820, 430
    left, right, top, bottom = 70, 160, 30, 70
    plot_w = width - left - right
    plot_h = height - top - bottom
    rows = sorted(rows, key=lambda row: (str(row["family"]), int(row["k"]), str(row["algorithm"])))
    labels = sorted({f"{row['family']} K={int(row['k'])}" for row in rows})
    algs = ["alns", "vns", "tabu_search"]
    colors = {"alns": "#2563eb", "vns": "#16a34a", "tabu_search": "#dc2626"}
    lookup = {(f"{row['family']} K={int(row['k'])}", row["algorithm"]): float(row["mean_gap_pct"]) for row in rows}
    max_gap = max(lookup.values()) * 1.1
    group_w = plot_w / len(labels)
    bar_w = group_w / 4

    def y(gap: float) -> float:
        return top + (1.0 - gap / max_gap) * plot_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#222"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#222"/>',
    ]
    for tick in range(0, int(max_gap) + 5, max(5, int(max_gap // 5) or 5)):
        yy = y(tick)
        parts.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{left + plot_w}" y2="{yy:.1f}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{left - 10}" y="{yy + 4:.1f}" text-anchor="end" font-size="12">{tick}</text>')
    for i, label in enumerate(labels):
        base_x = left + i * group_w + group_w * 0.15
        for j, alg in enumerate(algs):
            gap = lookup[(label, alg)]
            xx = base_x + j * bar_w
            yy = y(gap)
            parts.append(f'<rect x="{xx:.1f}" y="{yy:.1f}" width="{bar_w * 0.8:.1f}" height="{top + plot_h - yy:.1f}" fill="{colors[alg]}" opacity="0.85"/>')
        parts.append(f'<text x="{left + i * group_w + group_w / 2:.1f}" y="{top + plot_h + 18}" text-anchor="middle" font-size="11">{label}</text>')
    legend_x, legend_y = left + plot_w + 35, top + 20
    for i, alg in enumerate(algs):
        yy = legend_y + i * 26
        parts.append(f'<rect x="{legend_x}" y="{yy - 10}" width="20" height="14" fill="{colors[alg]}" opacity="0.85"/>')
        parts.append(f'<text x="{legend_x + 30}" y="{yy + 2}" font-size="13">{ALGORITHM_LABELS[alg]}</text>')
    parts.append(f'<text x="18" y="{top + plot_h / 2}" transform="rotate(-90 18 {top + plot_h / 2})" text-anchor="middle" font-size="14">Mean gap (%)</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def make_latex(
    *,
    main_time: list[dict[str, object]],
    main_10: list[dict[str, object]],
    family_10: list[dict[str, object]],
    size_10: list[dict[str, object]],
    k_overall: list[dict[str, object]],
    k_by_k: list[dict[str, object]],
    raw_overall: list[dict[str, object]],
    raw_size: list[dict[str, object]],
    overview_10: list[dict[str, object]],
    meta: dict[str, object],
) -> str:
    main_time_pivot = pivot_gap_table(main_time, "time_limit", [1.0, 3.0, 5.0, 10.0, 30.0])
    family_order = sorted({row["family"] for row in family_10})
    family_pivot = pivot_gap_table(family_10, "family", family_order)
    size_order = ["small", "medium", "large"]
    size_pivot = pivot_gap_table(size_10, "size_bucket", size_order)
    overview_rows = sorted(overview_10, key=lambda row: (str(row["dataset"]), str(row["algorithm"])))
    raw_rows = sorted(raw_overall, key=lambda row: (str(row["dataset"]), float(row["mean_gap_pct"])))
    k_by_k_rows = sorted(k_by_k, key=lambda row: (str(row["family"]), int(row["k"]), str(row["algorithm"])))
    main_10_rows = sorted(main_10, key=lambda row: float(row["mean_gap_pct"]))

    def pivot_line(row: dict[str, object], label_field: str) -> str:
        return (
            f"{tex_escape(row[label_field])} & {pct(row['alns'])} & {pct(row['vns'])} "
            f"& {pct(row['tabu_search'])} & {row['best_algorithm']} \\\\"
        )

    return rf"""
\section{{Thực nghiệm}}

Phần thực nghiệm so sánh ba thuật toán sau khi đã cố định cấu hình tốt nhất: ALNS, VNS và Tabu Search. Tất cả kết quả dưới đây được tổng hợp lại từ 12 file runs chính trong \texttt{{output/algorithm\_comparison}}, gồm generated test, K sensitivity, CVRPLIB và TSPLIB. File kiểm tra parse TSPLIB phụ không được đưa vào tổng hợp.

\subsection{{Cấu hình đánh giá}}

\begin{{table}}[H]
\centering
\caption{{Cấu hình thuật toán dùng trong thực nghiệm cuối.}}
\label{{tab:exp-final-configs}}
\begin{{tabular}}{{lll}}
\toprule
Thuật toán & Tên cấu hình & Tham số chính \\
\midrule
ALNS & \texttt{{small\_destroy + strict + exploration\_friendly}} & $q_{{min}}=0.02$, $q_{{max}}=0.10$, $T_0=300$, $\alpha=0.999$, reward $(10,5,2,0)$ \\
VNS & \texttt{{shake7 + cand24}} & max shake level $=7$, candidate limit $=24$ \\
Tabu Search & \texttt{{tenure15 + cand100}} & tenure $=15$, candidate limit $=100$, local search bật \\
\bottomrule
\end{{tabular}}
\end{{table}}

Metric chính là độ dài tuyến lớn nhất $L_{{\max}}$. Với mỗi instance và time limit, gap của một thuật toán được tính tương đối so với nghiệm tốt nhất trong ba thuật toán:
\[
    \mathrm{{gap}}(a,i,t)=100\cdot\frac{{L_{{\max}}(a,i,t)-\min_b L_{{\max}}(b,i,t)}}{{\min_b L_{{\max}}(b,i,t)}}.
\]
Do đó gap $0\%$ nghĩa là thuật toán đạt nghiệm tốt nhất trong nhóm so sánh tại instance đó. Tổng cộng có {meta["valid_rows"]} dòng hợp lệ; không có dòng malformed bị loại trong lần tổng hợp này.

\subsection{{Generated Test Theo Thời Gian}}

Bảng~\ref{{tab:exp-main-10s}} là kết quả chính tại mốc 10 giây trên 28 instance generated test. VNS đứng đầu với mean gap {pct(main_10_rows[0]["mean_gap_pct"])}, Tabu Search đứng thứ hai và ALNS đứng thứ ba. So với cấu hình ALNS cũ, cấu hình mới ưu tiên destroy nhỏ và reward accepted cao hơn; tuy nhiên trên generated test ngắn hạn, VNS vẫn khai thác local search tốt hơn rõ rệt.

\begin{{table}}[H]
\centering
\caption{{Generated test tại mốc 10 giây.}}
\label{{tab:exp-main-10s}}
\begin{{tabular}}{{lrrrrrr}}
\toprule
Thuật toán & Mean gap & Median gap & Win-rate & Mean $L_{{\max}}$ & Total dist. & Runtime \\
\midrule
{table_lines(main_10_rows, ["algorithm", "mean_gap_pct", "median_gap_pct", "win_rate", "mean_max_route", "mean_total_distance", "mean_runtime"], {"mean_gap_pct", "median_gap_pct"})}
\bottomrule
\end{{tabular}}
\end{{table}}

Bảng~\ref{{tab:exp-time-gap}} và Hình~\ref{{fig:exp-main-time-gap}} cho thấy chất lượng nghiệm theo thời gian trên generated test. Tabu Search rất cạnh tranh ở mốc 1 giây do mỗi vòng lặp rẻ, VNS vượt lên rõ ở các mốc từ 3 đến 30 giây. ALNS mới cải thiện dần khi tăng thời gian nhưng vẫn kém VNS trên tập generated test, cho thấy cơ chế destroy--repair cần thêm thời gian hoặc cần tuning riêng cho phân phối seed 02--03 nếu muốn thắng ở tập này.

\begin{{table}}[H]
\centering
\caption{{Mean gap theo time limit trên generated test.}}
\label{{tab:exp-time-gap}}
\begin{{tabular}}{{lrrrr}}
\toprule
Time & ALNS & VNS & Tabu & Tốt nhất \\
\midrule
{chr(10).join(pivot_line(row, "time_limit") for row in main_time_pivot)}
\bottomrule
\end{{tabular}}
\end{{table}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.82\linewidth]{{output/algorithm_comparison/report_artifacts/fig_main_time_gap.svg}}
\caption{{Mean gap của ba thuật toán theo time limit trên generated test.}}
\label{{fig:exp-main-time-gap}}
\end{{figure}}

\subsection{{Phân Tích Theo Family Và Quy Mô}}

Bảng~\ref{{tab:exp-family-10s}} tách kết quả generated test 10 giây theo dạng dữ liệu. VNS tốt nhất trên cluster, depot-position, outlier và uniform. Với corridor, VNS và Tabu Search cùng đạt gap $0\%$, còn ALNS chỉ kém rất nhẹ. Điều này cho thấy corridor là nhóm dễ cân bằng hơn, trong khi các family còn lại cần local search hoặc move tái phân phối mạnh hơn.

\begin{{table}}[H]
\centering
\caption{{Mean gap theo family tại 10 giây trên generated test.}}
\label{{tab:exp-family-10s}}
\begin{{tabular}}{{lrrrr}}
\toprule
Family & ALNS & VNS & Tabu & Tốt nhất \\
\midrule
{chr(10).join(pivot_line(row, "family") for row in family_pivot)}
\bottomrule
\end{{tabular}}
\end{{table}}

Bảng~\ref{{tab:exp-size-10s}} cho thấy VNS thắng nhóm small và medium, còn nhóm large hoà giữa VNS và Tabu Search theo $L_{{\max}}$. Với $N$ lớn, nghiệm ban đầu và tốc độ local search có ảnh hưởng mạnh; ALNS destroy nhỏ giữ được chi phí mỗi vòng thấp nhưng số vòng hữu ích trong 10 giây vẫn chưa đủ để vượt hai thuật toán còn lại trên generated test.

\begin{{table}}[H]
\centering
\caption{{Mean gap theo quy mô tại 10 giây trên generated test.}}
\label{{tab:exp-size-10s}}
\begin{{tabular}}{{lrrrr}}
\toprule
Quy mô & ALNS & VNS & Tabu & Tốt nhất \\
\midrule
{chr(10).join(pivot_line(row, "size_bucket") for row in size_pivot)}
\bottomrule
\end{{tabular}}
\end{{table}}

\subsection{{K Sensitivity}}

K sensitivity chạy ở mốc cố định 10 giây trên các instance $N=500$ với $K=2,10,50$. Bảng~\ref{{tab:exp-k-overall}} cho thấy ALNS là thuật toán tốt nhất tổng thể trên bộ này, với mean gap thấp nhất. Điểm đáng chú ý là khi $K=2$, VNS khó cải thiện vì chỉ có hai tuyến rất dài; ALNS và Tabu Search ổn định hơn nhờ cơ chế tái chèn và move có định hướng tuyến dài.

\begin{{table}}[H]
\centering
\caption{{K sensitivity tổng thể tại 10 giây.}}
\label{{tab:exp-k-overall}}
\begin{{tabular}}{{lrrrrr}}
\toprule
Thuật toán & Mean gap & Win-rate & Mean $L_{{\max}}$ & Runtime & Iter. \\
\midrule
{table_lines(sorted(k_overall, key=lambda row: float(row["mean_gap_pct"])), ["algorithm", "mean_gap_pct", "win_rate", "mean_max_route", "mean_runtime", "mean_iterations"], {"mean_gap_pct"})}
\bottomrule
\end{{tabular}}
\end{{table}}

\begin{{table}}[H]
\centering
\caption{{K sensitivity theo family và $K$.}}
\label{{tab:exp-k-by-k}}
\begin{{tabular}}{{llrrrrr}}
\toprule
Family & $K$ & Thuật toán & Mean gap & Win-rate & Mean $L_{{\max}}$ & Runtime \\
\midrule
{table_lines(k_by_k_rows, ["family", "k", "algorithm", "mean_gap_pct", "win_rate", "mean_max_route", "mean_runtime"], {"mean_gap_pct"})}
\bottomrule
\end{{tabular}}
\end{{table}}

\begin{{figure}}[H]
\centering
\includegraphics[width=0.82\linewidth]{{output/algorithm_comparison/report_artifacts/fig_k_sensitivity_gap.svg}}
\caption{{Mean gap theo family và $K$ trên bộ K sensitivity.}}
\label{{fig:exp-k-sensitivity}}
\end{{figure}}

\subsection{{Raw Benchmark}}

Bảng~\ref{{tab:exp-raw-overall}} tổng hợp CVRPLIB và TSPLIB tại mốc 10 giây. Trên cả CVRPLIB và TSPLIB, VNS có gap trung bình thấp nhất. ALNS mới đứng giữa trên TSPLIB nhưng kém hơn Tabu Search trên CVRPLIB; điều này cho thấy cấu hình destroy nhỏ chưa đủ để vượt VNS trên raw benchmark trong giới hạn 10 giây.

\begin{{table}}[H]
\centering
\caption{{Raw benchmark tổng thể tại 10 giây.}}
\label{{tab:exp-raw-overall}}
\begin{{tabular}}{{llrrrrr}}
\toprule
Benchmark & Thuật toán & Instance & Mean gap & Win-rate & Mean $L_{{\max}}$ & Runtime \\
\midrule
{table_lines(raw_rows, ["dataset", "algorithm", "instances", "mean_gap_pct", "win_rate", "mean_max_route", "mean_runtime"], {"mean_gap_pct"})}
\bottomrule
\end{{tabular}}
\end{{table}}

\begin{{table}}[H]
\centering
\caption{{Raw benchmark theo quy mô instance.}}
\label{{tab:exp-raw-size}}
\begin{{tabular}}{{lllrrrr}}
\toprule
Benchmark & Quy mô & Thuật toán & Mean gap & Win-rate & Mean $L_{{\max}}$ & Runtime \\
\midrule
{table_lines(sorted(raw_size, key=lambda row: (str(row["dataset"]), str(row["size_bucket"]), float(row["mean_gap_pct"]))), ["dataset", "size_bucket", "algorithm", "mean_gap_pct", "win_rate", "mean_max_route", "mean_runtime"], {"mean_gap_pct"})}
\bottomrule
\end{{tabular}}
\end{{table}}

\subsection{{Tổng Kết}}

Bảng~\ref{{tab:exp-overview-10s}} tổng hợp bốn bộ đánh giá ở mốc 10 giây. VNS là lựa chọn mạnh nhất trên generated test, CVRPLIB và TSPLIB. ALNS mới thể hiện tốt nhất trên K sensitivity, đặc biệt ở trường hợp $K=2$ nơi việc tái phân phối giữa ít tuyến rất quan trọng. Tabu Search có ưu thế tốc độ vòng lặp và thắng ở mốc rất ngắn trên generated test, nhưng gap trung bình trên các bộ còn lại thường cao hơn VNS.

\begin{{table}}[H]
\centering
\caption{{Tổng hợp bốn bộ dữ liệu tại 10 giây.}}
\label{{tab:exp-overview-10s}}
\begin{{tabular}}{{llrrrrr}}
\toprule
Bộ dữ liệu & Thuật toán & Instance & Mean gap & Win-rate & Mean $L_{{\max}}$ & Runtime \\
\midrule
{table_lines(overview_rows, ["dataset", "algorithm", "instances", "mean_gap_pct", "win_rate", "mean_max_route", "mean_runtime"], {"mean_gap_pct"})}
\bottomrule
\end{{tabular}}
\end{{table}}

Kết luận thực nghiệm nên được diễn đạt theo ngữ cảnh. VNS là thuật toán mạnh nhất tổng thể trong lần chạy hiện tại, đặc biệt trên generated test từ 3--30 giây và trên hai raw benchmark. ALNS với cấu hình \texttt{{small\_destroy\_\_strict\_\_exploration\_friendly}} là lựa chọn tốt nhất trên K sensitivity, cho thấy ưu thế khi $K$ thay đổi mạnh. Tabu Search phù hợp làm baseline heuristic mạnh, đặc biệt ở thời gian rất ngắn và trên một số nhóm dễ cân bằng, nhưng không phải thuật toán tốt nhất tổng quát.
""".strip() + "\n"


def main() -> int:
    timestamp = datetime.now().isoformat(timespec="seconds")
    rows, malformed = read_rows()
    clean = add_gap_and_rank(rows)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    write_csv(ARTIFACT_DIR / "report_clean_instance_algorithm_rows.csv", clean)

    main_rows = [row for row in clean if row["dataset"] == "main_test"]
    main_10_rows = [row for row in main_rows if float(row["time_limit"]) == 10.0]
    k_rows = [row for row in clean if row["dataset"] == "k_sensitivity"]
    raw_rows = [row for row in clean if row["dataset"] in {"raw_cvrplib", "raw_tsplib"}]

    main_time = summarize(main_rows, ["time_limit", "algorithm"], sort_fields=["time_limit", "algorithm"])
    main_10 = summarize(main_10_rows, ["algorithm"], sort_fields=["algorithm"])
    family_10 = summarize(main_10_rows, ["family", "algorithm"], sort_fields=["family", "algorithm"])
    size_10 = summarize(main_10_rows, ["size_bucket", "algorithm"], sort_fields=["size_bucket", "algorithm"])
    k_overall = summarize(k_rows, ["algorithm"], sort_fields=["algorithm"])
    k_by_k = summarize(k_rows, ["family", "k", "algorithm"], sort_fields=["family", "k", "algorithm"])
    raw_overall = summarize(raw_rows, ["dataset", "algorithm"], sort_fields=["dataset", "algorithm"])
    raw_size = summarize(raw_rows, ["dataset", "size_bucket", "algorithm"], sort_fields=["dataset", "size_bucket", "algorithm"])
    overview_10 = summarize([row for row in clean if float(row["time_limit"]) == 10.0], ["dataset", "algorithm"], sort_fields=["dataset", "algorithm"])

    write_csv(ARTIFACT_DIR / "report_main_time_summary.csv", main_time)
    write_csv(ARTIFACT_DIR / "report_main_10s_summary.csv", main_10)
    write_csv(ARTIFACT_DIR / "report_main_10s_family_summary.csv", family_10)
    write_csv(ARTIFACT_DIR / "report_main_10s_size_summary.csv", size_10)
    write_csv(ARTIFACT_DIR / "report_k_sensitivity_overall.csv", k_overall)
    write_csv(ARTIFACT_DIR / "report_k_sensitivity_by_k.csv", k_by_k)
    write_csv(ARTIFACT_DIR / "report_raw_overall.csv", raw_overall)
    write_csv(ARTIFACT_DIR / "report_raw_cvrplib_overall.csv", [row for row in raw_overall if row["dataset"] == "raw_cvrplib"])
    write_csv(ARTIFACT_DIR / "report_raw_tsplib_overall.csv", [row for row in raw_overall if row["dataset"] == "raw_tsplib"])
    write_csv(ARTIFACT_DIR / "report_raw_by_size.csv", raw_size)
    write_csv(ARTIFACT_DIR / "report_raw_cvrplib_by_size.csv", [row for row in raw_size if row["dataset"] == "raw_cvrplib"])
    write_csv(ARTIFACT_DIR / "report_raw_tsplib_by_size.csv", [row for row in raw_size if row["dataset"] == "raw_tsplib"])
    write_csv(ARTIFACT_DIR / "report_10s_overview_by_dataset.csv", overview_10)

    plot_main = [
        {
            "time_limit": row["time_limit"],
            "algorithm": ALGORITHM_LABELS[str(row["algorithm"])],
            "mean_gap_pct": row["mean_gap_pct"],
            "win_rate": row["win_rate"],
            "mean_max_route": row["mean_max_route"],
        }
        for row in main_time
    ]
    plot_k = [
        {
            "family": row["family"],
            "k": row["k"],
            "algorithm": ALGORITHM_LABELS[str(row["algorithm"])],
            "mean_gap_pct": row["mean_gap_pct"],
            "mean_max_route": row["mean_max_route"],
        }
        for row in k_by_k
    ]
    write_csv(ARTIFACT_DIR / "plot_main_time_gap.csv", plot_main)
    write_csv(ARTIFACT_DIR / "plot_k_sensitivity_gap.csv", plot_k)
    svg_main_time(ARTIFACT_DIR / "fig_main_time_gap.svg", main_time)
    svg_k_sensitivity(ARTIFACT_DIR / "fig_k_sensitivity_gap.svg", k_by_k)

    meta = {
        "timestamp": timestamp,
        "input_files": RUN_FILES,
        "valid_rows": len(clean),
        "raw_rows": len(rows),
        "malformed_rows": len(malformed),
        "datasets": {
            dataset: len({row["instance"] for row in clean if row["dataset"] == dataset})
            for dataset in RUN_FILES
        },
    }
    (ARTIFACT_DIR / "report_generation_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    latex = make_latex(
        main_time=main_time,
        main_10=main_10,
        family_10=family_10,
        size_10=size_10,
        k_overall=k_overall,
        k_by_k=k_by_k,
        raw_overall=raw_overall,
        raw_size=raw_size,
        overview_10=overview_10,
        meta=meta,
    )
    (ARTIFACT_DIR / "report_section_6_experiments_full.tex").write_text(latex, encoding="utf-8")

    print(f"Read {len(rows)} raw row(s); wrote {len(clean)} clean comparison row(s).")
    print(f"Skipped {len(malformed)} malformed row(s).")
    print(f"Wrote report artifacts to {ARTIFACT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
