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
Lấy  max_len tuyến dài nhất
     sum_len tổng quãng đường của các tuyến
     max_len - min_len khoảng chênh giữa tuyến dài nhất và tuyến ngắn nhất

Khi có 2 lời giải có max bằng nhau:
    - sum nhở hơn thì chọn (tổng quãng đường ít hơn)
    - max - min nhỏ hơn (các tuyến đều nhau hơn)
"""
def objective_from_lengths(lengths):
    values = list(lengths)
    if not values:
        return (0.0, 0.0, 0.0)
    max_len = max(values)
    return (max_len, sum(values), max_len - min(values))

def objective(routes, d):
    return objective_from_lengths(all_length(routes, d))

#độ dài thay đổi bao nhiêu khi chèn point vào route tại position
def insertion_delta(route, point, position, d):
    prev = route[position - 1]
    # chèn vào giữa
    if position < len(route):
        next_node = route[position]
        return d[prev][point] + d[point][next_node] - d[prev][next_node]
    # chèn vào cuối
    return d[prev][point]

#Khởi tạo tham lam
def greedy_init(N, K, d):
    routes = [[0] for _ in range(K)]
    lengths = [0.0] * K

    # điểm xa nhất xử lý trước
    points = sorted(range(1, N + 1), key=lambda p: d[0][p], reverse=True)

    for point in points:
        best = None
        total = sum(lengths)

        for r_idx in range(K):
            other_max = max((lengths[i] for i in range(K) if i != r_idx), default=0.0)
            for pos in range(1, len(routes[r_idx]) + 1):
                delta = insertion_delta(routes[r_idx], point, pos, d)
                new_len = lengths[r_idx] + delta
                score = (max(other_max, new_len), total + delta, new_len)
                if best is None or score < best[0]:
                    best = (score, r_idx, pos, delta)

        if best is None:
            continue
        _, r_idx, pos, delta = best
        routes[r_idx].insert(pos, point)
        lengths[r_idx] += delta

    return routes

# Loại Move

#Relocate: lấy điểm point ra khỏi tuyến src ở vị trí src_pos chèn vào tuyến dst sau vị trí dst_pos
def apply_relocate(routes, src, src_pos, dst, dst_pos):
    new_routes = copy.deepcopy(routes)
    point = new_routes[src].pop(src_pos)
    # nếu dời trong cùng tun thì sau khi xoá index bị dịch
    if src == dst and dst_pos >= src_pos:
        dst_pos -= 1
    new_routes[dst].insert(dst_pos + 1, point)
    return new_routes

#Swap: Hoán đổi iểm p ở tuyến r1 vị trí pos1 với điểm q ở tuyến r2, vị trid pos2
def apply_swap(routes, r1, pos1, r2, pos2):
    new_routes = copy.deepcopy(routes)
    new_routes[r1][pos1], new_routes[r2][pos2] = new_routes[r2][pos2], new_routes[r1][pos1]
    return new_routes

#Reverse: đảo ngược đoạn [start..end]
def apply_reverse(routes, r_id, start, end):
    new_routes = copy.deepcopy(routes)
    new_routes[r_id][start:end + 1] = routes[r_id][start:end + 1][::-1]
    return new_routes

# Sinh láng giềng
def generate_candidate(routes, d, max_candidates = 200, deadline = None):
    """
    return: list tuple: (new_obj, move_type, tabu_attr, move_params)
    trong đó new_obj là tuple (max, sum, max-min)
    """
    lengths = all_length(routes, d)
    worst_idx = max(range(len(routes)), key=lambda i: lengths[i])
    K = len(routes)
    candidates = []

    src = worst_idx
    #relocate
    for src_pos in range(1, len(routes[src])):
        if deadline is not None and time.perf_counter() >= deadline:
            return candidates[:max_candidates]
        point = routes[src][src_pos]
        for dst in range(K):
            if dst == src: continue
            for dst_pos in range(len(routes[dst])):
                new_routes = apply_relocate(routes, src, src_pos, dst, dst_pos)
                new_obj = objective(new_routes, d)
                tabu_attr = ('relocate', point, dst)
                move_params = (src, src_pos, dst, dst_pos)
                candidates.append((new_obj, 'relocate', tabu_attr, move_params))

    #swap
    for pos1 in range(1, len(routes[src])):
        if deadline is not None and time.perf_counter() >= deadline:
            return candidates[:max_candidates]
        point1 = routes[src][pos1]
        for dst in range(K):
            if dst == src: continue
            for pos2 in range(1, len(routes[dst])):
                point2 = routes[dst][pos2]
                new_routes = apply_swap(routes, src, pos1, dst, pos2)
                new_obj = objective(new_routes, d)
                tabu_attr = ('swap', min(point1, point2), max(point1, point2))
                move_params = (src, pos1, dst, pos2)
                candidates.append((new_obj, 'swap', tabu_attr, move_params))

    #reverse
    for start in range(1, len(routes[src]) - 1):
        if deadline is not None and time.perf_counter() >= deadline:
            return candidates[:max_candidates]
        for end in range(start + 1, len(routes[src])):
            new_routes = apply_reverse(routes, src, start, end)
            new_obj = objective(new_routes, d)
            segment = tuple(new_routes[src][start:end + 1])
            tabu_attr = ('reverse', segment)
            move_params = (src, start, end)
            candidates.append((new_obj, 'reverse', tabu_attr, move_params))

    # sort theo new_obj tăng dần
    candidates = sorted(candidates, key=lambda x: x[0])
    return candidates[:max_candidates]

# tabu search
def tabu_search(N, K, d, max_inter=1000, tenure=7, max_candidates=200,
                include_return_to_depot=False, deadline=None):
    routes = greedy_init(N, K, d)
    best_routes = copy.deepcopy(routes)
    f_best = objective(routes, d)

    tabu_set = set()
    tabu_queue = deque()
    iterations_done = 0

    for interation in range(max_inter):
        if deadline is not None and time.perf_counter() >= deadline:
            break

        candidates = generate_candidate(routes, d, max_candidates, deadline)

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

    return best_routes, f_best[0], iterations_done

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
                    new_r = route[:i] + route[i:j + 1][::-1] + route[j + 1:]
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
        tenure=7,
        max_candidates=200,
        deadline=None  # đặt ví dụ time.perf_counter() + 60 để giới hạn 60 giây
    )

    best_routes = local_clear(best_routes, d)
    print_output(best_routes)


if __name__ == '__main__':
    main()