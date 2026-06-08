"""Generate report artifacts for ALNS tuning."""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TUNING_DIR = ROOT / "output" / "config_tuning" / "tuning_seed01_alns"


def latest(pattern: str) -> Path:
    paths = sorted(TUNING_DIR.glob(pattern), key=lambda path: path.stat().st_mtime)
    if not paths:
        raise FileNotFoundError(pattern)
    return paths[-1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def family_from_instance(instance: str) -> str:
    parts = Path(instance).parts
    if "generated" in parts:
        idx = parts.index("generated")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return "unknown"


def size_bucket(n: int, k: int) -> str:
    if n <= 150:
        return "small"
    if n <= 500:
        return "medium"
    return "large"


def group_stats(rows: list[dict[str, str]], group_fields: list[str]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[field] for field in group_fields)].append(row)

    out = []
    for key, group in grouped.items():
        rel = [f(row, "relative_max_route") for row in group]
        impr = [f(row, "max_route_improvement_pct") for row in group]
        max_routes = [f(row, "max_route") for row in group]
        totals = [f(row, "total_distance") for row in group]
        balances = [f(row, "balance") for row in group]
        runtimes = [f(row, "runtime") for row in group]
        iterations = [f(row, "iterations") for row in group]
        record: dict[str, object] = {field: value for field, value in zip(group_fields, key)}
        record.update(
            {
                "runs": len(group),
                "mean_relative_max_route": mean(rel),
                "mean_improvement_pct": mean(impr),
                "win_rate": sum(1 for value in rel if value < 1.0) / len(rel),
                "mean_max_route": mean(max_routes),
                "mean_total_distance": mean(totals),
                "mean_balance": mean(balances),
                "mean_runtime": mean(runtimes),
                "mean_iterations": mean(iterations),
            }
        )
        out.append(record)
    out.sort(
        key=lambda row: (
            tuple(str(row[field]) for field in group_fields[:-1]),
            float(row["mean_relative_max_route"]),
            float(row["mean_balance"]),
        )
    )
    return out


def pct(value: object, digits: int = 2) -> str:
    return f"{float(value):.{digits}f}\\%"


def num(value: object, digits: int = 2) -> str:
    return f"{float(value):.{digits}f}"


def latex_escape(text: object) -> str:
    return str(text).replace("_", "\\_")


def table_rows(rows: list[dict[str, object]], keys: list[str], pct_keys: set[str] | None = None) -> str:
    pct_keys = pct_keys or set()
    lines = []
    for row in rows:
        cells = []
        for key in keys:
            value = row[key]
            if key == "win_rate":
                cells.append(pct(float(value) * 100.0))
            elif key in pct_keys:
                cells.append(pct(value))
            elif key == "mean_relative_max_route":
                cells.append(num(value, 4))
            elif key.startswith("mean_") or key in {"mean_relative_max_route"}:
                cells.append(num(value))
            elif isinstance(value, float):
                cells.append(num(value))
            else:
                cells.append(latex_escape(value))
        lines.append(" & ".join(cells) + r" \\")
    return "\n".join(lines)


def svg_line_chart(path: Path) -> None:
    width, height = 760, 420
    left, right, top, bottom = 70, 35, 35, 60
    plot_w = width - left - right
    plot_h = height - top - bottom
    curves = [
        ("strict", 300.0, 0.999, "#1f77b4"),
        ("default", 1000.0, 0.999, "#2ca02c"),
        ("very exploratory", 1000.0, 0.9999, "#d62728"),
    ]
    xs = list(range(0, 3001, 100))
    delta = 100.0

    def map_x(x: float) -> float:
        return left + (x / 3000.0) * plot_w

    def map_y(y: float) -> float:
        return top + (1.0 - y) * plot_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#222"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#222"/>',
    ]
    for tick in range(0, 3001, 500):
        x = map_x(tick)
        parts.append(f'<line x1="{x:.1f}" y1="{top + plot_h}" x2="{x:.1f}" y2="{top + plot_h + 5}" stroke="#222"/>')
        parts.append(f'<text x="{x:.1f}" y="{top + plot_h + 24}" text-anchor="middle" font-size="12">{tick}</text>')
    for tick in [0.0, 0.25, 0.5, 0.75, 1.0]:
        y = map_y(tick)
        parts.append(f'<line x1="{left - 5}" y1="{y:.1f}" x2="{left}" y2="{y:.1f}" stroke="#222"/>')
        parts.append(f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" font-size="12">{tick:.2f}</text>')
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#e8e8e8"/>')
    parts.append(f'<text x="{left + plot_w / 2}" y="{height - 16}" text-anchor="middle" font-size="14">Iteration</text>')
    parts.append(f'<text x="18" y="{top + plot_h / 2}" transform="rotate(-90 18 {top + plot_h / 2})" text-anchor="middle" font-size="14">Acceptance probability for worse move, Delta=100</text>')

    for name, t0, cooling, color in curves:
        pts = []
        for x in xs:
            temp = t0 * (cooling**x)
            prob = math.exp(-delta / max(temp, 1e-12))
            pts.append(f"{map_x(x):.1f},{map_y(prob):.1f}")
        parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="2.4"/>')
    legend_x, legend_y = 515, 52
    for i, (name, t0, cooling, color) in enumerate(curves):
        y = legend_y + i * 24
        parts.append(f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 28}" y2="{y}" stroke="{color}" stroke-width="3"/>')
        parts.append(f'<text x="{legend_x + 36}" y="{y + 4}" font-size="13">{name}: T0={t0:g}, alpha={cooling}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def svg_bar_chart(path: Path, rows: list[dict[str, str]]) -> None:
    rows = [row for row in rows if row["stage"] in {"baseline", "destroy_tuning", "sa_tuning", "reward_tuning", "final_selection"}]
    rows.sort(key=lambda row: (row["stage"], f(row, "mean_relative_max_route")))
    picked = []
    for stage in ["baseline", "destroy_tuning", "sa_tuning", "reward_tuning", "final_selection"]:
        stage_rows = [row for row in rows if row["stage"] == stage]
        if stage_rows:
            picked.append(stage_rows[0])
    width, height = 820, 420
    left, right, top, bottom = 75, 35, 35, 105
    plot_w = width - left - right
    plot_h = height - top - bottom
    max_impr = max(f(row, "mean_max_route_improvement_pct") for row in picked)
    min_impr = min(0.0, min(f(row, "mean_max_route_improvement_pct") for row in picked))
    span = max_impr - min_impr or 1.0

    def y(value: float) -> float:
        return top + (max_impr - value) / span * plot_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<line x1="{left}" y1="{y(0):.1f}" x2="{left + plot_w}" y2="{y(0):.1f}" stroke="#666"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#222"/>',
    ]
    bar_w = 88
    gap = (plot_w - bar_w * len(picked)) / max(1, len(picked) - 1)
    for i, row in enumerate(picked):
        value = f(row, "mean_max_route_improvement_pct")
        x = left + i * (bar_w + gap)
        y0 = y(0)
        yv = y(value)
        rect_y = min(y0, yv)
        rect_h = abs(y0 - yv)
        color = "#3b82f6" if value >= 0 else "#ef4444"
        parts.append(f'<rect x="{x:.1f}" y="{rect_y:.1f}" width="{bar_w}" height="{rect_h:.1f}" fill="{color}" opacity="0.85"/>')
        parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{rect_y - 8:.1f}" text-anchor="middle" font-size="12">{value:.2f}%</text>')
        label = row["group_key"].replace("_", " ")
        label = label[:24]
        parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{top + plot_h + 22}" text-anchor="middle" font-size="11">{row["stage"].replace("_", " ")}</text>')
        parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{top + plot_h + 40}" text-anchor="middle" font-size="10">{label}</text>')
    parts.append(f'<text x="{left + plot_w / 2}" y="{height - 18}" text-anchor="middle" font-size="14">Best group in each tuning stage</text>')
    parts.append(f'<text x="18" y="{top + plot_h / 2}" transform="rotate(-90 18 {top + plot_h / 2})" text-anchor="middle" font-size="14">Mean improvement over baseline (%)</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def main() -> int:
    runs_path = latest("*_alns_tuning_runs.csv")
    summary_path = latest("*_alns_tuning_summary.csv")
    selection_path = latest("*_alns_tuning_selection.csv")
    meta_path = latest("*_alns_tuning_meta.json")
    rows = read_csv(runs_path)
    summary = read_csv(summary_path)
    selection = read_csv(selection_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    for row in rows:
        row["family"] = family_from_instance(row["instance"])
        row["size_bucket"] = size_bucket(int(float(row["n"])), int(float(row["k"])))
        row["size_key"] = f"n={int(float(row['n']))}, k={int(float(row['k']))}"

    final_choice = next(row for row in selection if row["note"] == "chosen_config")
    final_config = final_choice["group_key"]
    selected_final_rows = [
        row
        for row in rows
        if row["config_name"] == final_config
        and row["stage"] in {"final_selection", "final_validation", "reward_tuning"}
    ]
    stage_tables = {
        "destroy": [row for row in summary if row["stage"] == "destroy_tuning"],
        "sa": [row for row in summary if row["stage"] == "sa_tuning"],
        "reward": [row for row in summary if row["stage"] == "reward_tuning"],
        "final": [row for row in summary if row["stage"] == "final_selection"],
    }
    for stage_rows in stage_tables.values():
        stage_rows.sort(key=lambda row: f(row, "mean_relative_max_route"))

    write_csv(TUNING_DIR / "report_alns_destroy_summary.csv", stage_tables["destroy"])
    write_csv(TUNING_DIR / "report_alns_sa_summary.csv", stage_tables["sa"])
    write_csv(TUNING_DIR / "report_alns_reward_summary.csv", stage_tables["reward"])
    write_csv(TUNING_DIR / "report_alns_final_summary.csv", stage_tables["final"])
    write_csv(TUNING_DIR / "report_alns_final_by_family.csv", group_stats(selected_final_rows, ["family"]))
    write_csv(TUNING_DIR / "report_alns_final_by_size.csv", group_stats(selected_final_rows, ["size_bucket", "size_key"]))
    write_csv(TUNING_DIR / "report_alns_destroy_by_size.csv", group_stats([row for row in rows if row["stage"] == "destroy_tuning"], ["size_bucket", "destroy_name"]))
    write_csv(TUNING_DIR / "report_alns_sa_by_size.csv", group_stats([row for row in rows if row["stage"] == "sa_tuning"], ["size_bucket", "sa_name"]))
    write_csv(TUNING_DIR / "report_alns_reward_by_size.csv", group_stats([row for row in rows if row["stage"] == "reward_tuning"], ["size_bucket", "reward_name"]))

    svg_line_chart(TUNING_DIR / "fig_alns_sa_acceptance.svg")
    svg_bar_chart(TUNING_DIR / "fig_alns_stage_improvement.svg", summary)

    baseline = next(row for row in summary if row["stage"] == "baseline")
    destroy_rows = stage_tables["destroy"]
    sa_rows = stage_tables["sa"]
    reward_rows = stage_tables["reward"]
    final_rows = stage_tables["final"]
    final_family = group_stats(selected_final_rows, ["family"])
    final_size = group_stats(selected_final_rows, ["size_bucket", "size_key"])
    destroy_size = group_stats([row for row in rows if row["stage"] == "destroy_tuning"], ["size_bucket", "destroy_name"])
    sa_size = group_stats([row for row in rows if row["stage"] == "sa_tuning"], ["size_bucket", "sa_name"])

    chosen_parts = final_config.split("__")
    chosen_destroy, chosen_sa, chosen_reward = chosen_parts
    latex = rf"""
\subsection{{Tinh chỉnh ALNS}}

Mục tiêu của bước tinh chỉnh ALNS là chọn một cấu hình cố định cho toàn bộ phần thực nghiệm sau đó. Metric chính của bài toán là độ dài tuyến lớn nhất $L_{{\max}}$, vì vậy toàn bộ quá trình tuning xếp hạng cấu hình theo tỉ lệ
\[
    \mathrm{{rel}}(c,i,s)=\frac{{L_{{\max}}(c,i,s)}}{{L_{{\max}}(c_0,i,s)}},
\]
trong đó $c$ là cấu hình đang xét, $i$ là instance, $s$ là seed của solver và $c_0$ là baseline chạy trên đúng cùng cặp $(i,s)$. Một cấu hình tốt có $\mathrm{{rel}}<1$, tức là cải thiện so với baseline. Cột improvement trong các bảng được tính bằng
\[
    100\cdot\frac{{L_{{\max}}(c_0,i,s)-L_{{\max}}(c,i,s)}}{{L_{{\max}}(c_0,i,s)}}.
\]
Do đó improvement dương là tốt hơn baseline, còn improvement âm nghĩa là cấu hình làm nghiệm xấu đi. Tie-break sau metric chính lần lượt ưu tiên balance nhỏ hơn, win-rate cao hơn và tổng quãng đường nhỏ hơn.

\paragraph{{Baseline.}}
Baseline dùng mức destroy trung bình, SA mặc định và reward mặc định:
\[
q_{{\min}}=0.05,\quad q_{{\max}}=0.20,\quad T_0=1000,\quad \alpha=0.999,\quad
(r_{{best}},r_{{cur}},r_{{acc}},r_{{rej}})=(10,5,1,0).
\]
Trên {len(meta["instances"])} instance và {len(meta["seeds"])} seed, baseline có {int(float(baseline["runs"]))} run, mean $L_{{\max}}={num(baseline["mean_max_route"], 2)}$, mean total distance ${num(baseline["mean_total_distance"], 2)}$, mean balance ${num(baseline["mean_balance"], 2)}$. Baseline này không phải cấu hình cuối cùng, mà là điểm neo để đo tác động riêng của từng nhóm tham số.

\begin{{table}}[H]
\centering
\caption{{Baseline ALNS dùng làm mốc so sánh.}}
\label{{tab:alns-baseline}}
\begin{{tabular}}{{lrrrrrr}}
\toprule
Cấu hình & Runs & Rel. $L_{{\max}}$ & Improvement & Win-rate & Mean $L_{{\max}}$ & Runtime \\
\midrule
baseline & {baseline["runs"]} & {num(baseline["mean_relative_max_route"], 4)} & {pct(baseline["mean_max_route_improvement_pct"])} & {pct(float(baseline["win_rate"]) * 100)} & {num(baseline["mean_max_route"], 2)} & {num(baseline["mean_runtime"], 2)} \\
\bottomrule
\end{{tabular}}
\end{{table}}

\paragraph{{Nhóm destroy-size.}}
Nhóm destroy quyết định số khách hàng bị tháo ra ở mỗi vòng ALNS. Với instance có $N$ khách hàng, số điểm bị destroy nằm xấp xỉ trong khoảng $[q_{{\min}}N,q_{{\max}}N]$. Nếu destroy quá nhỏ, thuật toán chỉ tinh chỉnh cục bộ; nếu quá lớn, mỗi vòng repair đắt hơn và nghiệm bị phá quá mạnh. Kết quả trong Bảng~\ref{{tab:alns-destroy}} cho thấy cấu hình \texttt{{small\_destroy}} là tốt nhất: mean relative $L_{{\max}}={num(destroy_rows[0]["mean_relative_max_route"], 4)}$, tương ứng cải thiện trung bình {pct(destroy_rows[0]["mean_max_route_improvement_pct"])} so với baseline và win-rate {pct(float(destroy_rows[0]["win_rate"]) * 100)}.

\begin{{table}}[H]
\centering
\caption{{So sánh nhóm destroy-size trên toàn bộ instance và seed.}}
\label{{tab:alns-destroy}}
\begin{{tabular}}{{lrrrrrr}}
\toprule
Cấu hình & Runs & Rel. $L_{{\max}}$ & Improvement & Win-rate & Mean $L_{{\max}}$ & Iter. \\
\midrule
{table_rows(destroy_rows, ["group_key", "runs", "mean_relative_max_route", "mean_max_route_improvement_pct", "win_rate", "mean_max_route", "mean_iterations"], { "mean_max_route_improvement_pct" })}
\bottomrule
\end{{tabular}}
\end{{table}}

Về mặt thuật toán, kết quả này hợp lý với Min--Max VRP. Mục tiêu $L_{{\max}}$ thường được cải thiện bằng cách dịch một số khách hàng khỏi tuyến dài nhất sang các tuyến còn dư tải, không nhất thiết phải phá một phần lớn nghiệm. Với $N=100$ hoặc $N=300$, destroy nhỏ vẫn đủ tạo lân cận có ý nghĩa nhưng cho phép nhiều vòng lặp hơn trong 5 giây. Với $N=1000,K=100$, destroy lớn làm bước repair quá nặng; số vòng lặp giảm mạnh nên khả năng học trọng số operator cũng kém hơn.

\begin{{table}}[H]
\centering
\caption{{Destroy-size theo quy mô instance.}}
\label{{tab:alns-destroy-size}}
\begin{{tabular}}{{llrrrr}}
\toprule
Quy mô & Destroy & Runs & Improvement & Win-rate & Iter. \\
\midrule
{table_rows(destroy_size, ["size_bucket", "destroy_name", "runs", "mean_improvement_pct", "win_rate", "mean_iterations"], { "mean_improvement_pct" })}
\bottomrule
\end{{tabular}}
\end{{table}}

\paragraph{{Nhóm Simulated Annealing.}}
SA quyết định xác suất chấp nhận một nghiệm xấu hơn nghiệm hiện tại:
\[
    p=\exp\left(-\frac{{\Delta}}{{T}}\right),\qquad T_t=T_0\alpha^t.
\]
Trong đó $\Delta$ là mức xấu đi của objective. Nếu $T_0$ quá cao hoặc $\alpha$ quá gần 1, thuật toán khám phá lâu hơn nhưng có thể tiêu tốn thời gian vào nghiệm không tốt. Nếu nhiệt độ quá thấp, thuật toán dễ kẹt cục bộ. Bảng~\ref{{tab:alns-sa}} cho thấy \texttt{{strict}} là lựa chọn tốt nhất, với $T_0=300,\alpha=0.999$. Điều này nghĩa là trên bộ tuning hiện tại, ALNS hưởng lợi từ việc chấp nhận nghiệm xấu một cách có kiểm soát thay vì quá exploratory.

\begin{{figure}}[H]
\centering
\includegraphics[width=0.82\linewidth]{{output/config_tuning/tuning_seed01_alns/fig_alns_sa_acceptance.svg}}
\caption{{Minh họa xác suất chấp nhận nghiệm xấu hơn trong SA khi $\Delta=100$. Cấu hình strict giảm xác suất chấp nhận nhanh hơn, còn very exploratory duy trì xác suất cao trong nhiều vòng lặp hơn.}}
\label{{fig:alns-sa-acceptance}}
\end{{figure}}

\begin{{table}}[H]
\centering
\caption{{So sánh nhóm Simulated Annealing.}}
\label{{tab:alns-sa}}
\begin{{tabular}}{{lrrrrrr}}
\toprule
Cấu hình & Runs & Rel. $L_{{\max}}$ & Improvement & Win-rate & Mean $L_{{\max}}$ & Runtime \\
\midrule
{table_rows(sa_rows, ["group_key", "runs", "mean_relative_max_route", "mean_max_route_improvement_pct", "win_rate", "mean_max_route", "mean_runtime"], { "mean_max_route_improvement_pct" })}
\bottomrule
\end{{tabular}}
\end{{table}}

Khi tách theo quy mô, khác biệt giữa các cấu hình SA không lớn ở nhóm lớn, còn nhóm nhỏ nghiêng rõ hơn về \texttt{{strict}}. Ở nhóm trung bình, \texttt{{default}} có improvement trung bình nhỉnh hơn nhưng \texttt{{strict}} có win-rate tốt hơn. Vì vậy cấu hình SA được chọn theo tổng hợp toàn bộ là \texttt{{strict}}, còn \texttt{{very\_exploratory}} được giữ làm ứng viên phụ cho vòng final để kiểm tra xem tăng exploration có cải thiện khi kết hợp với reward khác hay không.

\begin{{table}}[H]
\centering
\caption{{SA theo quy mô instance.}}
\label{{tab:alns-sa-size}}
\begin{{tabular}}{{llrrrr}}
\toprule
Quy mô & SA & Runs & Improvement & Win-rate & Runtime \\
\midrule
{table_rows(sa_size, ["size_bucket", "sa_name", "runs", "mean_improvement_pct", "win_rate", "mean_runtime"], { "mean_improvement_pct" })}
\bottomrule
\end{{tabular}}
\end{{table}}

\paragraph{{Nhóm reward.}}
Reward điều khiển adaptive weights của các destroy/repair operator. Một operator được tăng trọng số nhiều nếu tạo global best, tăng vừa nếu cải thiện nghiệm hiện tại, và vẫn có thể được thưởng khi nghiệm được chấp nhận. Bảng~\ref{{tab:alns-reward}} cho thấy xét riêng theo mean relative $L_{{\max}}$, \texttt{{default}} đứng đầu với improvement {pct(reward_rows[0]["mean_max_route_improvement_pct"])}. Tuy nhiên \texttt{{exploration\_friendly}} có win-rate cao nhất trong nhóm reward ({pct(float([row for row in reward_rows if row["group_key"] == "exploration_friendly"][0]["win_rate"]) * 100)}), do đó được giữ lại để kiểm tra ở vòng final. Cơ chế này hợp lý vì trong ALNS, một nghiệm được chấp nhận dù chưa cải thiện ngay vẫn có thể mở đường cho chuỗi move tốt hơn ở các vòng sau.

\begin{{table}}[H]
\centering
\caption{{So sánh nhóm reward của adaptive operator selection.}}
\label{{tab:alns-reward}}
\begin{{tabular}}{{lrrrrrr}}
\toprule
Cấu hình & Runs & Rel. $L_{{\max}}$ & Improvement & Win-rate & Mean $L_{{\max}}$ & Balance \\
\midrule
{table_rows(reward_rows, ["group_key", "runs", "mean_relative_max_route", "mean_max_route_improvement_pct", "win_rate", "mean_max_route", "mean_balance"], { "mean_max_route_improvement_pct" })}
\bottomrule
\end{{tabular}}
\end{{table}}

\paragraph{{Lựa chọn cuối cùng.}}
Vòng final ghép hai destroy tốt nhất, hai SA tốt nhất và hai reward tốt nhất. Kết quả trong Bảng~\ref{{tab:alns-final}} chọn \texttt{{{latex_escape(final_config)}}}. Cấu hình này dùng:
\[
q_{{\min}}=0.02,\quad q_{{\max}}=0.10,\quad T_0=300,\quad \alpha=0.999,\quad
(r_{{best}},r_{{cur}},r_{{acc}},r_{{rej}})=(10,5,2,0).
\]
So với baseline, cấu hình cuối cải thiện trung bình {pct(final_rows[0]["mean_max_route_improvement_pct"])} trên $L_{{\max}}$, win-rate {pct(float(final_rows[0]["win_rate"]) * 100)}, đồng thời giảm mean balance từ {num(baseline["mean_balance"], 2)} xuống {num(final_rows[0]["mean_balance"], 2)}. Điều này cho thấy cấu hình cuối không chỉ giảm tuyến dài nhất mà còn làm nghiệm cân bằng hơn.

\begin{{figure}}[H]
\centering
\includegraphics[width=0.82\linewidth]{{output/config_tuning/tuning_seed01_alns/fig_alns_stage_improvement.svg}}
\caption{{Cải thiện trung bình tốt nhất qua từng stage tuning của ALNS so với baseline.}}
\label{{fig:alns-stage-improvement}}
\end{{figure}}

\begin{{table}}[H]
\centering
\caption{{So sánh các cấu hình ở vòng final selection.}}
\label{{tab:alns-final}}
\begin{{tabular}}{{lrrrrrr}}
\toprule
Cấu hình & Runs & Rel. $L_{{\max}}$ & Improvement & Win-rate & Mean $L_{{\max}}$ & Balance \\
\midrule
{table_rows(final_rows, ["group_key", "runs", "mean_relative_max_route", "mean_max_route_improvement_pct", "win_rate", "mean_max_route", "mean_balance"], { "mean_max_route_improvement_pct" })}
\bottomrule
\end{{tabular}}
\end{{table}}

\paragraph{{Phân tích theo dạng instance.}}
Bảng~\ref{{tab:alns-final-family}} cho thấy cấu hình cuối cải thiện rõ nhất trên nhóm outlier, sau đó là depot-position và uniform. Điều này hợp lý vì outlier thường tạo một vài khách hàng làm tuyến dài bị nghẽn; destroy nhỏ kết hợp repair theo Min--Max có thể tháo đúng các điểm này và phân phối lại sang tuyến còn dư. Với depot-position và uniform, cải thiện vẫn dương nhưng nhỏ hơn vì cấu trúc hình học đều hơn hoặc bị chi phối bởi vị trí depot. Corridor gần như hoà với baseline, còn cluster giảm nhẹ; hai nhóm này cho thấy destroy nhỏ không phải lúc nào cũng đủ để đảo cấu trúc cụm hoặc hành lang nếu tuyến dài nhất chịu ảnh hưởng bởi hình học tổng thể.

\begin{{table}}[H]
\centering
\caption{{Cấu hình ALNS cuối theo từng họ instance.}}
\label{{tab:alns-final-family}}
\begin{{tabular}}{{lrrrrrr}}
\toprule
Family & Runs & Improvement & Win-rate & Mean $L_{{\max}}$ & Total dist. & Balance \\
\midrule
{table_rows(final_family, ["family", "runs", "mean_improvement_pct", "win_rate", "mean_max_route", "mean_total_distance", "mean_balance"], { "mean_improvement_pct" })}
\bottomrule
\end{{tabular}}
\end{{table}}

\paragraph{{Phân tích theo $N,K$.}}
Với $N=100,K=5$, mỗi lần destroy chỉ tháo khoảng 2--10 khách hàng, đủ để sửa tuyến dài mà vẫn chạy được nhiều iteration. Với $N=300,K=20$, số điểm tháo khoảng 6--30, phù hợp cho tái phân phối giữa nhiều tuyến hơn. Với $N=1000,K=100$, số điểm tháo khoảng 20--100; đây là mức vẫn còn khả thi trong giới hạn thời gian, trong khi các cấu hình large destroy có thể tháo 100--300 hoặc 150--400 điểm và làm repair quá nặng. Vì vậy cấu hình \texttt{{small\_destroy}} là lựa chọn hợp lý khi $N$ và $K$ tăng: neighborhood vẫn đủ rộng theo số tuyệt đối, nhưng không làm mất quá nhiều thời gian cho mỗi vòng lặp.

\begin{{table}}[H]
\centering
\caption{{Cấu hình ALNS cuối theo quy mô $N,K$.}}
\label{{tab:alns-final-size}}
\begin{{tabular}}{{llrrrrr}}
\toprule
Quy mô & $N,K$ & Runs & Improvement & Win-rate & Mean $L_{{\max}}$ & Iter. \\
\midrule
{table_rows(final_size, ["size_bucket", "size_key", "runs", "mean_improvement_pct", "win_rate", "mean_max_route", "mean_iterations"], { "mean_improvement_pct" })}
\bottomrule
\end{{tabular}}
\end{{table}}

Tóm lại, kết quả tuning cho thấy ALNS trong bài toán Min--Max VRP nên ưu tiên destroy nhỏ, SA tương đối strict và reward vẫn khuyến khích nghiệm được chấp nhận. Cấu hình cuối \texttt{{{latex_escape(final_config)}}} cân bằng tốt ba yếu tố: đủ exploration để thoát local optimum, đủ exploitation để tập trung vào tuyến dài nhất, và đủ nhanh để chạy nhiều vòng trên cả nhóm $N=100$, $N=300$ và $N=1000$.
""".strip()
    (TUNING_DIR / "report_section_5_3_alns_tuning.tex").write_text(latex + "\n", encoding="utf-8")

    print(f"Using runs: {runs_path.relative_to(ROOT)}")
    print(f"Using summary: {summary_path.relative_to(ROOT)}")
    print(f"Chosen config: {final_config}")
    print(f"Wrote report artifacts to: {TUNING_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
