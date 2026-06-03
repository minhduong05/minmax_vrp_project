import os
import glob
import time
import csv
import sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from vns import Instance, solve, all_routes_length

# Colors cho Terminal
RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"

def load_references(csv_path):
    refs = {}
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Bộ mtsplib có instance là 'berlin52' và k='2', ta gộp thành 'berlin52_k2'
            # Bộ hustack có instance là 'tc1', ta giữ nguyên
            inst = row["instance"]
            if "tc" not in inst and "k" in row:
                key = f"{inst}_k{row['k']}"
            else:
                key = inst
                
            refs[key] = {
                "max_route": int(row["objective_max_route"]),
                "total_dist": int(row["total_distance"]),
                "source_file": row.get("source_file", "")
            }
    return refs

def get_gap(val, ref):
    if ref == 0: return 0.0
    return ((val - ref) / ref) * 100

def get_status_and_color(my_max, ref_max):
    if my_max < ref_max:
        return "better_max", GREEN
    elif my_max == ref_max:
        return "matched", GREEN
    elif my_max <= ref_max * 1.05:
        return "worse_max", YELLOW
    else:
        return "worse_max", RED

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Đổi sang test bộ IBM CPLEX (mtsplib_minmax)
    data_dir = os.path.join(base_dir, "data", "mtsplib_minmax")
    ref_file = os.path.join(data_dir, "reference.csv")
    
    if not os.path.exists(ref_file):
        print(f"Không tìm thấy {ref_file}")
        return
        
    refs = load_references(ref_file)
    test_files = glob.glob(os.path.join(data_dir, "*.txt"))
    # Sort alphabet
    test_files.sort()
    
    # In Header Bảng ASCII
    print(CYAN + "╔══════════════╦═════╦════╦═══════════════╦═══════════════╦════════════════════════╦═══════════════╦═════════════════╦══════════╦══════════════════════════╗" + RESET)
    print(CYAN + "║ Testcase     ║ N   ║ K  ║ Max Route     ║ Ref Max Route ║ Max Gap (%) & Status   ║ Total Dist    ║ Ref Total Dist  ║ Time (s) ║ Source File (Bản gốc)    ║" + RESET)
    print(CYAN + "╠══════════════╬═════╬════╬═══════════════╬═══════════════╬════════════════════════╬═══════════════╬═════════════════╬══════════╬══════════════════════════╣" + RESET)
    
    results = []
    
    for fpath in test_files:
        instance_name = os.path.basename(fpath).replace(".txt", "")
        if instance_name not in refs:
            continue
            
        with open(fpath, "r", encoding="utf-8") as f:
            lines = f.read().split()
            
        if not lines:
            continue
            
        n = int(lines[0])
        k = int(lines[1])
        size = n + 1
        dist = []
        idx = 2
        for _ in range(size):
            row = []
            for _ in range(size):
                row.append(int(lines[idx]))
                idx += 1
            dist.append(row)
            
        inst = Instance(n, k, dist)
        
        start_time = time.time()
        # Chạy thuật toán VNS của user
        best_sol = solve(inst)
        exec_time = time.time() - start_time
        
        if not best_sol:
            continue
            
        lengths = all_routes_length(best_sol, inst.distance)
        my_max = max(lengths) if lengths else 0
        my_total = sum(lengths) if lengths else 0
        
        ref = refs[instance_name]
        ref_max = ref["max_route"]
        ref_total = ref["total_dist"]
        source_file = ref["source_file"]
        
        gap_max = get_gap(my_max, ref_max)
        gap_total = get_gap(my_total, ref_total)
        
        status, color = get_status_and_color(my_max, ref_max)
        
        gap_str = f"{gap_max:6.2f}% ({status})"
        
        # In Row
        print(f"║ {instance_name:<12} ║ {n:<3} ║ {k:<2} ║ {my_max:<13} ║ {ref_max:<13} ║ {color}{gap_str:<22}{RESET} ║ {my_total:<13} ║ {ref_total:<15} ║ {exec_time:<7.3f}s ║ {source_file:<24} ║")
        
        results.append({
            "instance": instance_name,
            "n": n,
            "k": k,
            "max_route": my_max,
            "reference_max_route": ref_max,
            "max_route_gap_percent": round(gap_max, 2),
            "total_distance": my_total,
            "reference_total_distance": ref_total,
            "total_distance_gap_percent": round(gap_total, 2),
            "status": status,
            "runtime": round(exec_time, 3)
        })
        
    print(CYAN + "╚══════════════╩═════╩════╩═══════════════╩═══════════════╩════════════════════════╩═══════════════╩═════════════════╩══════════╩══════════════════════════╝" + RESET)
    
    # Save Log CSV
    out_dir = os.path.join(base_dir, "outputs", "logs")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "comparison_with_reference.csv")
    
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["instance", "n", "k", "max_route", "reference_max_route", "max_route_gap_percent", "total_distance", "reference_total_distance", "total_distance_gap_percent", "status", "runtime"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
        
    print(f"\\n[XONG] Đã xuất log CSV chuẩn xác ra thư mục: {out_file}")

if __name__ == "__main__":
    main()
