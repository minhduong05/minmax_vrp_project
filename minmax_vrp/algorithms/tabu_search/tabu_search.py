import copy
import sys
from collections import deque


def read_input():
    N, K = map(int, input().split())

    d = []
    for i in range(N + 1):
        row  = list(map(int, input().split()))
        d.append(row)

    return N, K, d

# tính tổng khoảng cách của một tuyến đường
def route_lenght(route, d):
    sum = 0
    for i in range(len(route) - 1):
        sum += d[route[i]][route[i + 1]]
    return sum

# lấy list độ dài các tuyến đường
def all_lengths(routes, d):
    return [route_lenght(route, d) for route in routes]

# lấy tuyến đường dài nhất
def longest_route(routes, d):
    return max(route_lenght(route, d) for  route in routes)

# khỏi tạo phương án ban đầu
def init(N, K, d):
    routes = [[0] for _ in range(K)]
    lenghts = [0] * K

    # sort các điểm giao hàng theo thứ tự giảm dần của khoảng cách từ kho
    points = sorted(range(1, N + 1), key=lambda i: -d[0][i])

    for p in points:
        k = lenghts.index(max(lenghts))
        last = routes[k][-1]
        routes[k].append(p)
        lenghts[k] += d[last][p] # di tu last -> p
    return routes

# các toán tử di chuyển giữa các tuyến đường hay ở trong chính tuyến đường đó

# Lấy điểm p ở vị trí pos1 của tuyến r1 rồi chèn vào sau vị trí pos2 của tuyến r2
def apply_relocate(routes, r1, pos1, r2, pos2):
    new_routes = copy.deepcopy(routes)
    p = new_routes[r1].pop(pos1)
    new_routes[r2].insert(pos2 + 1, p)
    return new_routes

#tính kết quả sau khi thay đổi
def delta_relocate(routes, r1, pos1, r2, pos2, d):
    route1 = routes[r1]
    route2 = routes[r2]
    p = route1[pos1]

    old_len1 = route_lenght(route1, d)
    new_r1 = route1[:pos1] + route2[pos1 + 1:]
    new_len1 = route_lenght(new_r1, d)

    old_len2 = route_lenght(route2, d)
    rew_r2 = route2[:pos2 + 1] + [p] + route1[pos2 + 1:]
    new_len2 = route_lenght(rew_r2, d)

    lengths = all_lengths(routes, d)
    lengths[r1] = new_len1
    lengths[r2] = new_len2
    return max(lengths)

# hoán đổi vị trí của pos1 của tuyến r1 với vị trí pos2 của tuyến r2
def apply_swap(routes, r1, pos1, r2, pos2):
    new_routes = copy.deepcopy(routes)
    new_routes[r1][pos1], new_routes[r2][pos2] = new_routes[r2][pos2], new_routes[r1][pos1]
    return new_routes

#tính kết quả sau khi thay đổi
def delta_swap(routes, r1, pos1, r2, pos2, d):
    route1 = routes[r1]
    route2 = routes[r2]
    p = route1[pos1]
    q = route2[pos2]

    new_r1 = route1[:pos1] + [q] + route1[pos1 + 1:]
    new_r2 = route2[:pos2] + [p] + route2[pos2 + 1:]

    lengths = all_lengths(routes, d)
    lengths[r1] = route_lenght(new_r1, d)
    lengths[r2] = route_lenght(new_r2, d)
    return max(lengths)

# đảo ngược một đoạn [i...j] trong 1 tuyến r
def apply_reverse(routes, r, i, j):
    new_routes = copy.deepcopy(routes)
    new_routes[r][i: j + 1] = new_routes[r][i: j + 1][::-1]
    return new_routes

# tính kết quả sau khi thay đổi
def delta_reverse(routes, r, i, j, d):
    route = routes[r]
    new_r = route[:i] + route[i: j + 1][::-1] + route[j + 1:]

    lengths = all_lengths(routes, d)
    lengths[r] = route_lenght(new_r, d)
    return max(lengths)

# tạo các láng giềng (candidates)
def generative_candidates(routes, d, max_candidates=200):
    lengths = all_lengths(routes, d)
    longest_idx = lengths.index(max(lengths))
    K = len(routes)

    candidates = []

    # relocate
    r1 = longest_idx
    for pos1 in range(1, len(routes[r1])):
        p = routes[r1][pos1]
        for r2 in range(K):
            if r2 == r1: continue
            for pos2 in range(len(routes[r2])):
                new_f = delta_relocate(routes, r1, pos1, r2, pos2, d)
                tabu_attr = ('relocate', p, r1) # lấy p từ r1 cho sang tuyến khác
                move_params = (r1, pos1, r2, pos2)
                candidates.append((new_f, 'relocate', tabu_attr, move_params))

    #swap
    for pos1 in range(1, len(routes[r1])):
        p = routes[r1][pos1]
        for r2 in range(K):
            if r2 == r1: continue
            for pos2 in range(1, len(routes[r2])):
                q = routes[r2][pos2]
                new_f = delta_swap(routes, r1, pos1, r2, pos2, d)
                tabu_attr = ('swap', min(p, q), max(p, q))
                move_params = (r1, pos1, r2, pos2)
                candidates.append((new_f, 'swap', tabu_attr, move_params))

    #reverse
    for i in range(1, len(routes[r1]) - 1):
        for j in range(i + 1, len(routes[r1])):
            new_f = delta_reverse(routes, r1, i, j, d)
            tabu_attr = ('reverse', i, j)
            move_params = (r1, i, j)
            candidates.append((new_f, 'reverse', tabu_attr, move_params))

    candidates.sort(key=lambda x: x[0]) # sắp xếp theo new_f tăng dần

    return candidates[:max_candidates]

# tabu search
def tabu_search(N, K, d, max_inter=1000, tenure=7, max_candidates=200):
    # khởi tạo lời giải ban đầu
    routes = init(N, K, d)
    best_routes = copy.deepcopy(routes)
    f_best = longest_route(routes, d)

    #tabu list
    tabu_set = set()
    tabu_queue = deque()

    # lặp
    for iteration in range(max_inter):
        candidates = generative_candidates(routes, d, max_candidates)

        if not candidates:
            break

        chosen = None

        for (new_f, move_type, tabu_attr, move_params) in candidates:
            if tabu_attr not in tabu_set:
                chosen = (new_f, move_type, tabu_attr, move_params)
                break
            else:
                if new_f < f_best:
                    chosen = (new_f, move_type, tabu_attr, move_params)
                    break

        if chosen is None:
            chosen = candidates[0]

        new_f, move_type, tabu_attr, move_params = chosen

        if move_type == 'relocate':
            r1, pos1, r2, pos2 = move_params
            routes = apply_relocate(routes, r1, pos1, r2, pos2)
        if move_type == 'swap':
            r1, pos1, r2, pos2 = move_params
            routes = apply_swap(routes, r1, pos1, r2, pos2)
        if move_type == 'reverse':
            r, i, j = move_params
            routes = apply_reverse(routes, r, i, j)

        current_f = longest_route(routes, d)
        if current_f < f_best:
            f_best = current_f
            best_routes = copy.deepcopy(routes)

        # cập nhật tabu list
        tabu_queue.append(tabu_attr)
        tabu_set.add(tabu_attr)
        if len(tabu_queue) > tenure:
            old_attr = tabu_queue.popleft()
            tabu_set.discard(old_attr)

    return best_routes, f_best

# tối ưu thứ tự đi tron từng tuyến
def local_clear(routes, d):
    improved = True
    while improved:
        improved = False
        for id in range(len(routes)):
            route = routes[id]
            if len(route) < 3: continue
            for i in range(1, len(route) - 1):
                for j in range(i + 1, len(route)):
                    old_len = route_lenght(route, d)
                    new_r = route[:i] + route[i:j + 1][::-1] + route[j + 1:]
                    new_len = route_lenght(new_r, d)
                    if new_len < old_len:
                        routes[id] = new_r
                        route = new_r
                        improved = True
    return routes

def output(routes, d):
    K = len(routes)
    print(K)
    for route in routes:
        lk = len(route)
        long = route_lenght(route, d)
        print("long: ", long)
        print(lk)
        print(' '.join(map(str, route)))

def main():
    N, K, d = read_input()
    best_routes, f_best = tabu_search(N, K, d)
    best_routes = local_clear(best_routes, d)
    output(best_routes, d)

if __name__ == '__main__':
    main()