import random
import sys
import copy
import time
from collections import deque

from ...models import Distance


def read_input():
    first = input().replace('\ufeff', '').split()
    N = int(first[0])
    K = int(first[1])

    d = []
    for i in range(N + 1):
        row = list(map(float, input().split()))
        d.append(row)

    return N, K, d


# dộ dài tuyến
def route_length(route, d):
    if len(route) <= 1:
        return 0.0
    total = 0
    for i in range(len(route) - 1):
        total += d[route[i]][route[i + 1]]
    return total


# list độ dài từng tuyến
def all_length(routes, d):
    return [route_length(r, d) for r in routes]


"""
TIEU CHI SO SANH THONG NHAT TOAN BAI:
    score = (vector do dai cac tuyen sap GIAM DAN, tong quang duong)

So sanh lexicographic tren vector giam dan = CAN BANG TAI manh hon chi xet max:
  - tuyen dai nhat nho hon  -> tot hon (giong uu tien giam max)
  - neu tuyen dai nhat bang -> xet tuyen dai NHI, roi dai BA, ...
    => keo TAT CA cac tuyen ve deu nhau (khong chi quan tam max va min)
  - neu vector y het         -> moi xet tong quang duong (total) de tie-break
"""


def objective_from_lengths(lengths):
    values = list(lengths)
    if not values:
        return ((), 0.0)
    return (tuple(sorted(values, reverse=True)), sum(values))


def objective(routes, d):
    return objective_from_lengths(all_length(routes, d))


# độ dài thay đổi bao nhiêu khi chèn point vào route tại position
def insertion_delta(route, point, position, d):
    prev = route[position - 1]
    # chèn vào giữa
    if position < len(route):
        next_node = route[position]
        return d[prev][point] + d[point][next_node] - d[prev][next_node]
    # chèn vào cuối
    return d[prev][point]


# Khởi tạo tham lam
def greedy_init(N, K, d, rng=None):
    routes = [[0] for _ in range(K)]
    lengths = [0.0] * K

    # điểm xa nhất xử lý trước
    points = sorted(range(1, N + 1), key=lambda p: d[0][p], reverse=True)

    if rng is not None:
        shuffled = points[:]
        rng.shuffle(shuffled)
        # lay ~mot nua dau theo thu tu xa-nhat, mot nua sau theo thu tu ngau nhien
        cut = len(points) // 2
        kept = points[:cut]
        kept_set = set(kept)
        tail = [p for p in shuffled if p not in kept_set]
        points = kept + tail
        # them mot it xao tron toan cuc nhe cho da dang hon
        for _ in range(max(1, len(points) // 4)):
            i = rng.randrange(len(points))
            j = rng.randrange(len(points))
            points[i], points[j] = points[j], points[i]

    for point in points:
        best = None
        total = sum(lengths)
        empties = [i for i in range(K) if len(routes[i]) == 1]
        allowed = empties if empties else range(K)
        for r_idx in allowed:
            temp_lengths = list(lengths)
            for pos in range(1, len(routes[r_idx]) + 1):
                delta = insertion_delta(routes[r_idx], point, pos, d)
                temp_lengths[r_idx] = lengths[r_idx] + delta
                score = (tuple(sorted(temp_lengths, reverse=True)), total + delta)
                if best is None or score < best[0]:
                    best = (score, r_idx, pos, delta)

        if best is None:
            continue
        _, r_idx, pos, delta = best
        routes[r_idx].insert(pos, point)
        lengths[r_idx] += delta

    return routes


# Loại Move

# Relocate: lấy điểm point ra khỏi tuyến src ở vị trí src_pos chèn vào tuyến dst sau vị trí dst_pos
def apply_relocate(routes, src, src_pos, dst, dst_pos):
    new_routes = copy.deepcopy(routes)
    point = new_routes[src].pop(src_pos)
    # nếu dời trong cùng tuyến thì sau khi xoá index bị dịch
    if src == dst and dst_pos >= src_pos:
        dst_pos -= 1
    new_routes[dst].insert(dst_pos + 1, point)
    return new_routes


# Swap: Hoán đổi iểm p ở tuyến r1 vị trí pos1 với điểm q ở tuyến r2, vị trid pos2
def apply_swap(routes, r1, pos1, r2, pos2):
    new_routes = copy.deepcopy(routes)
    new_routes[r1][pos1], new_routes[r2][pos2] = new_routes[r2][pos2], new_routes[r1][pos1]
    return new_routes


# Reverse: đảo ngược đoạn [start..end]
def apply_reverse(routes, r_id, start, end):
    new_routes = copy.deepcopy(routes)
    new_routes[r_id][start:end + 1] = routes[r_id][start:end + 1][::-1]
    return new_routes


# sự thay đổi khi bỏ điểm tại vị tr pos khỏi route
def _remove_delta(route, pos, d):
    prev = route[pos - 1]
    cur = route[pos]
    if pos + 1 < len(route):
        nxt = route[pos + 1]
        return d[prev][nxt] - d[prev][cur] - d[cur][nxt]
    return -d[prev][cur]


# sự thay đổi khi chèn point vào sau vị trí pos của route
def _insert_delta(route, point, pos, d):
    prev = route[pos]
    if pos + 1 < len(route):
        nxt = route[pos + 1]
        return d[prev][point] + d[point][nxt] - d[prev][nxt]
    return d[prev][point]


# Sinh láng giềng
def generate_candidate(routes, d, max_candidates=100, deadline=None, num_target_routes=12):
    """
    return: list tuple: (new_obj, move_type, tabu_attr, move_params)
    trong đó new_obj là tuple (max, sum, max-min)
    """
    lengths = all_length(routes, d)
    total = sum(lengths)
    K = len(lengths)
    worst_idx = max(range(K), key=lambda i: lengths[i])
    best_idx = min(range(K), key=lambda i: lengths[i])
    src = worst_idx

    # num_targer_routes tuyen ngan nhat
    other = sorted((i for i in range(K) if i != src), key=lambda i: lengths[i])
    targets = other[:num_target_routes]

    # num_targer_routes tuyen dai nhat
    long_sources = sorted(
        (i for i in range(K) if i != best_idx), key=lambda i: lengths[i], reverse=True
    )[:num_target_routes]

    candidates = []

    # tính lại objective khi beiét độ dài mới của tối đa 2 tuyến
    def obj_with_changes(changed):
        new_lengths = list(lengths)
        new_sum = total
        for i, v in changed.items():
            new_sum += v - lengths[i]
            new_lengths[i] = v
        return (tuple(sorted(new_lengths, reverse=True)), new_sum)

    # kéo điểm từ các tuyến dài về tuyến ngắn nhất để cân bằng tải
    dst = best_idx
    for s in long_sources:
        if len(routes[s]) <= 2:
            continue
        if deadline is not None and time.perf_counter() >= deadline:
            return sorted(candidates, key=lambda x: x[0])[:max_candidates]
        for s_pos in range(1, len(routes[s])):
            point = routes[s][s_pos]
            rd = _remove_delta(routes[s], s_pos, d)
            new_len_s = lengths[s] + rd
            for dpos in range(len(routes[dst])):
                ins = _insert_delta(routes[dst], point, dpos, d)
                new_len_dst = lengths[dst] + ins
                new_obj = obj_with_changes({s: new_len_s, dst: new_len_dst})
                tabu_attr = ("relocate", point, dst)
                move_params = (s, s_pos, dst, dpos)
                candidates.append((new_obj, "relocate", tabu_attr, move_params))

    # relocate kéo điểm từ tuyến dài nhất về các tuyến ngắn nhất
    if len(routes[src]) > 2:
        for src_pos in range(1, len(routes[src])):
            if deadline is not None and time.perf_counter() >= deadline:
                return sorted(candidates, key=lambda x: x[0])[:max_candidates]
            point = routes[src][src_pos]
            rd = _remove_delta(routes[src], src_pos, d)
            new_len_src = lengths[src] + rd
            for dst in targets:  # chỉ tuyến ngắn nhất
                for dst_pos in range(len(routes[dst])):
                    ins = _insert_delta(routes[dst], point, dst_pos, d)  # O(1)
                    new_len_dst = lengths[dst] + ins
                    new_obj = obj_with_changes({src: new_len_src, dst: new_len_dst})
                    tabu_attr = ("relocate", point, dst)
                    move_params = (src, src_pos, dst, dst_pos)
                    candidates.append((new_obj, "relocate", tabu_attr, move_params))

    # swap
    for pos1 in range(1, len(routes[src])):
        if deadline is not None and time.perf_counter() >= deadline:
            return sorted(candidates, key=lambda x: x[0])[:max_candidates]
        point1 = routes[src][pos1]
        for dst in targets:
            for pos2 in range(1, len(routes[dst])):
                point2 = routes[dst][pos2]
                # swap = thay point1 bằng point2 TẠI CHỖ trong src,
                #        và thay point2 bằng point1 TẠI CHỖ trong dst.
                # Vị trí không đổi → chỉ cần đổi 2 cạnh kề mỗi điểm.
                # src: ...a - point1 - b...  ->  ...a - point2 - b...
                a1 = routes[src][pos1 - 1]
                if pos1 + 1 < len(routes[src]):
                    b1 = routes[src][pos1 + 1]
                    ds = (d[a1][point2] + d[point2][b1]) - (d[a1][point1] + d[point1][b1])
                else:
                    ds = d[a1][point2] - d[a1][point1]  # point1 là cuối tuyến
                new_len_src = lengths[src] + ds
                # dst: ...c - point2 - e...  ->  ...c - point1 - e...
                c2 = routes[dst][pos2 - 1]
                if pos2 + 1 < len(routes[dst]):
                    e2 = routes[dst][pos2 + 1]
                    dd = (d[c2][point1] + d[point1][e2]) - (d[c2][point2] + d[point2][e2])
                else:
                    dd = d[c2][point1] - d[c2][point2]  # point2 là cuối tuyến
                new_len_dst = lengths[dst] + dd
                new_obj = obj_with_changes({src: new_len_src, dst: new_len_dst})
                tabu_attr = ("swap", min(point1, point2), max(point1, point2))
                move_params = (src, pos1, dst, pos2)
                candidates.append((new_obj, "swap", tabu_attr, move_params))

    # reverse
    rsrc = routes[src]
    for start in range(1, len(rsrc) - 1):
        if deadline is not None and time.perf_counter() >= deadline:
            return sorted(candidates, key=lambda x: x[0])[:max_candidates]
        for end in range(start + 1, len(rsrc)):
            a = rsrc[start - 1]
            b = rsrc[start]
            c = rsrc[end]
            if end + 1 < len(rsrc):
                e = rsrc[end + 1]
                # bỏ cạnh a-b và c-e; thêm a-c và b-e
                delta = d[a][c] + d[b][e] - d[a][b] - d[c][e]
            else:
                # đoạn đảo chạm cuối tuyến: chỉ đổi cạnh a-b thành a-c
                delta = d[a][c] - d[a][b]
            new_len_src = lengths[src] + delta
            new_obj = obj_with_changes({src: new_len_src})
            segment = tuple(rsrc[start: end + 1])
            tabu_attr = ("reverse", segment)
            move_params = (src, start, end)
            candidates.append((new_obj, "reverse", tabu_attr, move_params))

    # sort theo new_obj tăng dần
    candidates = sorted(candidates, key=lambda x: x[0])
    return candidates[:max_candidates]


# tabu search
def tabu_search(N, K, d, max_inter=1000, tenure=15, max_candidates=100, deadline=None, seed=None, num_target_routes=12):
    rng = random.Random(seed) if seed is not None else None
    routes = greedy_init(N, K, d, rng)
    best_routes = copy.deepcopy(routes)
    f_best = objective(routes, d)

    tabu_set = set()
    tabu_queue = deque()
    iterations_done = 0

    for interation in range(max_inter):
        if deadline is not None and time.perf_counter() >= deadline:
            break

        candidates = generate_candidate(routes, d, max_candidates, deadline, num_target_routes)

        if not candidates:
            break

        chosen = None

        for (new_obj, move_type, tabu_attr, move_params) in candidates:
            if tabu_attr not in tabu_set:
                chosen = (new_obj, move_type, tabu_attr, move_params)
                break
            else:
                if new_obj < f_best:
                    chosen = (new_obj, move_type, tabu_attr, move_params)
                    break

        # nếu mọi move đều bị cấm
        if chosen is None:
            chosen = candidates[0]

        new_obj, move_type, tabu_attr, move_params = chosen

        if move_type == 'relocate':
            routes = apply_relocate(routes, *move_params)
        elif move_type == 'swap':
            routes = apply_swap(routes, *move_params)
        elif move_type == 'reverse':
            routes = apply_reverse(routes, *move_params)

        current_obj = objective(routes, d)
        if current_obj < f_best:
            f_best = current_obj
            best_routes = copy.deepcopy(routes)

        tabu_queue.append(tabu_attr)
        tabu_set.add(tabu_attr)
        if len(tabu_queue) > tenure:
            old_attr = tabu_queue.popleft()
            tabu_set.discard(old_attr)
        iterations_done += 1

    max_route = f_best[0][0] if f_best[0] else 0.0
    return best_routes, max_route, iterations_done


# tối ưu thứ tự ưu tiên
def local_clear(routes, d, include_return_to_depot=False):
    routes = copy.deepcopy(routes)
    improved = True
    while improved:
        improved = False
        for r_id in range(len(routes)):
            route = routes[r_id]
            if len(route) < 3:
                continue
            best_route = route
            best_len = route_length(route, d)
            for i in range(1, len(route) - 1):
                for j in range(i + 1, len(route)):
                    new_r = route[:i] + route[i: j + 1][::-1] + route[j + 1:]
                    new_len = route_length(new_r, d)
                    if new_len < best_len:
                        best_route = new_r
                        best_len = new_len
            if best_route is not route:
                routes[r_id] = best_route
                route = best_route
                improved = True
    return routes


def print_output(routes):
    K = len(routes)
    print(K)
    for route in routes:
        print(len(route))
        print(' '.join(map(str, route)))


def main():
    N, K, d = read_input()

    best_routes, f_best, _ = tabu_search(
        N, K, d,
        max_inter=800,
        tenure=15,
        max_candidates=100,
        deadline=None,
        num_target_routes=12
    )

    best_routes = local_clear(best_routes, d)
    print_output(best_routes)


if __name__ == '__main__':
    main()
