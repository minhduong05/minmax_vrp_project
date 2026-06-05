import time
import random

import copy
import sys

# hyperpara
TIME_LIMIT = 3.8
RANDOM_SEED = 42
MAX_SHAKE_LEVEL = 5
CANDIDATE_LIMIT = 24  # tham lam
MAX_VND_LEVEL = 3

# thấy bảo array tính toán nhanh hơn list :))
# boi den gsa (
# gsd[
# gsr[()

"""
mã giả vns:
    khởi tạo giải pháp ban đầu(dùng tham lam)
    x = vnd(x) // dung local search để tối ưu giải pháp ban đầu
    x_best = x // ghi lại đây là giải pháp tối nhất hiện tại
vòng lặp (chạy cho tới khi timeout)
    đăt k = 1 // thằng k được gọi là mức độ lắc , k càng lớn shank càng mạnh
    vòng lặp shank(cho tới k <= kmax)
        shank :
            lắc tạo ra giải pháp mới x'
        local search :
            x'' = vnd(x')
        neighborhoodchange :(đánh giá qua hàm đánh giá kết hợp quanlify function )
            nếu x'' tốt hơn x'
                x' = x''
                reset k = 1 // cho lắc lại với mức nhẹ nhất
            nếu x'' tệ hơn hoặc bằng x'
                k = k + 1 // lắc mạnh hơn
            nếu x'' tốt hơn x_best
                x_best = x''

timout : trả về x_best
"""

"""
mã giả vnd:
    khởi tạo các cấu trúc lân cận neighborhood  n1 , n2 , vvvv
    l = 1 // dùng lân cận đầu tiên
    vòng lặp(chạy đến hết các cấu trúc )
        tìm giả pháp x_new tốt nhất trong vùng lân gội nl của x
        nêu x_new tốt hơn x:
            x = x_new
            l = 1 // lại reset lại

        nếu x_new kém hơn hoặc bằng :
            l = l + 1
    trả về x
"""


# class chứa input
class Instance:
    def __init__(self, n, k, distance):
        self.n = n  # số điểm thu bưu kiện
        self.k = k  # sô thằng bưu tá
        self.distance = distance  # ma trận khoảng cách


def route_length(route, d):
    """
       tổng quãng đường của 1 tuyến giao hàng
       route: 1 tuyến giao hàng, danh sách các địa điểm giao hàng
       d : ma trận khoảng cách
       hình như méo tính đoạn trở về điểm 0
    a"""
    if len(route) <= 1:
        return 0
    length = sum(d[route[i]][route[i + 1]] for i in range(len(route) - 1))
    return length


def all_routes_length(routes, d):
    """
    tổng quãng đường chô mỗi tuyến -> trả về list
    routes: danh sách k tuyến
    d : ma trận khoảng cách
    """
    return [route_length(route, d) for route in routes]


# tả về dạng nghiệm dể so sánh với nhau, quantify function
def objective_from_lengths(lengths):
    """
    lengths : danh sách độ dài của k tuyến xe.
    Dùng tuple(sorted) giảm dần để giải quyết triệt để bài toán Min-Max bị kẹt Local Optima.
    """
    return tuple(sorted(lengths, reverse=True))


def objective_from_two(lengths, s, ns_length, d, nd_length):
    """
    Đưa ra dạng nghiệm so sánh được khi mà có sự thay đổi độ dài
    """
    old_s = lengths[s]
    old_d = lengths[d]

    lengths[s] = ns_length
    lengths[d] = nd_length

    res = tuple(sorted(lengths, reverse=True))

    lengths[s] = old_s
    lengths[d] = old_d
    return res


# delta evaluation : tối ưu chi phí


def insertion_delta(route, point, position, d):
    """
    tính số chi phí tăng lên khi chèn point vào vị trí position
    route : tuyến đường
    ponit : điểm cần chèn .
    position : vị trị điểm cần chèn
    d :
    """
    # do diểm xuât phát mặc định là 0 nên ko chèn vào đầu
    prev = route[position - 1]
    if position < len(route):
        next_node = route[position]
        return d[prev][point] + d[point][next_node] - d[prev][next_node]
    return d[prev][point]


def remove_delta(route, position, d):
    """
    Sô chi phí giảm bớt khi bỏ 1 diểm ở vị trí position
    """
    # không được vứt điểm xuất phát
    prev = route[position - 1]
    cur = route[position]
    if position < len(route) - 1:
        next_node = route[position + 1]
        return d[prev][cur] + d[cur][next_node] - d[prev][next_node]
    return d[prev][cur]


def replace_delta(route, position, point, d):
    """
    Sô chi phí thay đổi khi thay 1 diểm bằng điểm khác
    """
    prev = route[position - 1]
    cur = route[position]
    if position < len(route) - 1:
        next_node = route[position + 1]
        return d[prev][point] + d[point][next_node] - d[prev][cur] - d[cur][next_node]
    return d[prev][point] - d[prev][cur]


def two_opt_delta(route, startPos, endPos, d):
    """
    Số chi phí thay đổi khi dao nguoc 1 đoạn từ startPos tới endPos
    """

    # ma trận đối xứng nên các cạnh nội bộ của đoạn đảo không đổi -> chỉ còn 2 cạnh biên (O(1))
    prev = route[startPos - 1]
    s = route[startPos]
    e = route[endPos]

    if endPos < len(route) - 1:
        next_node = route[endPos + 1]
        return d[prev][e] + d[s][next_node] - d[prev][s] - d[e][next_node]
    return d[prev][e] - d[prev][s]


# VND
# Các cấu trúc lân cận


def best_relocate(routes, instance, deadline):
    """
    Tuyến nào dài nhất ? Rút bớt 1 point đưa cho thằng khác rảnh hơn
    Tìm danh sách tuyến dài nhất  A
    Lưu lại qf của routes hiện tại
    vòng lặp  từng tuyến B trong A
        Vòng lặp từng địa điểm C trong B
            Rút C khỏi B . lưu lại length của tuyến B sau khi rút C
            Vòng lặp từng tuyến B` khác B trong danh sách các tuyến D
                Vòng lặp từng địa điểm C' trong B'
                    Nhét C vào trước C'. lưu lại length của tuyến B sau khi nhét C vào tuyến B'.
                    so sánh (dùng quanlify func ) lưu lại kết quả tốt nhất (obj,vi tri rut, tuyen rut, vi tri nhet, tuyen nhet  )

    Nếu khong tìm được kết quả tốt nhất : qf mới là none ,hoặc qf mới kém hơn qf của routes hiện tại
        return
    Nếu tìm được thì hãy thực thi nước đi đó .
    Input : routes hiện tại, instance , deadline
    output : routes mới tốt hơn hoặc bằng
    """
    d = instance.distance
    lengths = all_routes_length(routes, d)
    # Luwu lai qf, objetive
    current_obj = objective_from_lengths(lengths)

    # Tìm List các tuyến dài nhất
    longest = current_obj[0]
    sources = [idx for idx, length in enumerate(lengths) if length == longest]
    best_move = None

    for src in sources:
        route_src = routes[src]
        for i in range(1, len(route_src)):
            if time.perf_counter() >= deadline:
                return None
            point = route_src[i]

            # Tinh độ dài tuyến sau khi rút C ra khỏi  B
            save = remove_delta(route_src, i, d)
            src_new_len = lengths[src] - save
            # Nhet no vao cac tuyen khac tru route_src
            for dst in range(len(routes)):
                if dst == src:
                    continue
                route_dst = routes[dst]
                for j in range(1, len(route_dst) + 1):
                    save = insertion_delta(route_dst, point, j, d)
                    dst_new_len = lengths[dst] + save

                    obj_new = objective_from_two(lengths, src, src_new_len, dst, dst_new_len)
                    if best_move is None or obj_new < best_move[0]:
                        best_move = (obj_new, i, src, j, dst)

    if best_move is None or best_move[0] >= current_obj:
        return None
    _, ps, src, pd, dst = best_move
    moved = routes[src].pop(ps)
    routes[dst].insert(pd, moved)
    return routes


def best_swap(routes, instance, deadline):
    """
    Tìm nước đi Swap TỐT NHẤT. Lấy 1 điểm từ tuyến dài nhất đổi lấy 1 điểm tuyến khác.
    Tương tự, duyệt lấy list các đường đi dài nhất. Duyệt từng tuyến, mỗi tuyến duyệt từng điểm để đổi . Sau mỗi lần đổi thì check xem kết quả có tốt hơn hay ko lưu vào best .
    Hết vòng lặp thì swwap trên route
    Trả về route sau khi swap
    """
    d = instance.distance
    lengths = all_routes_length(routes, d)
    current_obj = objective_from_lengths(lengths)

    longest = current_obj[0]
    sources = [idx for idx, length in enumerate(lengths) if length == longest]
    best_move = None

    for src in sources:
        route_src = routes[src]
        for i in range(1, len(route_src)):
            if time.perf_counter() >= deadline:
                return None
            point_src = route_src[i]

            for dst in range(len(routes)):
                if dst == src:
                    continue
                route_dst = routes[dst]
                for j in range(1, len(route_dst)):
                    point_dst = route_dst[j]

                    delta_src = replace_delta(route_src, i, point_dst, d)
                    src_new_len = lengths[src] + delta_src

                    delta_dst = replace_delta(route_dst, j, point_src, d)
                    dst_new_len = lengths[dst] + delta_dst

                    obj_new = objective_from_two(lengths, src, src_new_len, dst, dst_new_len)

                    if best_move is None or obj_new < best_move[0]:
                        best_move = (obj_new, i, src, j, dst)

    if best_move is None or best_move[0] >= current_obj:
        return None

    _, ps, src, pd, dst = best_move
    routes[src][ps], routes[dst][pd] = routes[dst][pd], routes[src][ps]
    return routes


def best_two_opt(routes, instance, deadline):
    """
    Gỡ nút chữ X (2-opt) trên tuyến dài nhất.
    """
    d = instance.distance
    lengths = all_routes_length(routes, d)
    current_obj = objective_from_lengths(lengths)

    longest = current_obj[0]
    sources = [idx for idx, length in enumerate(lengths) if length == longest]
    best_move = None

    for src in sources:
        route_src = routes[src]
        n_points = len(route_src)
        if n_points < 4:
            continue

        for i in range(1, n_points - 2):
            if time.perf_counter() >= deadline:
                return None
            for j in range(i + 1, n_points - 1):
                delta = two_opt_delta(route_src, i, j, d)

                # Chỉ đánh giá nếu độ dài thực sự giảm (tức là delta < 0)
                if delta < 0:
                    new_len = lengths[src] + delta
                    # Mô phỏng objective mới khi chỉ 1 tuyến thay đổi
                    temp = lengths.copy()
                    temp[src] = new_len
                    obj_new = objective_from_lengths(temp)

                    if best_move is None or obj_new < best_move[0]:
                        best_move = (obj_new, src, i, j)

    if best_move is None or best_move[0] >= current_obj:
        return None

    _, src, i, j = best_move
    route = routes[src]
    # Đảo ngược đoạn từ i đến j
    route[i : j + 1] = reversed(route[i : j + 1])
    return routes


def vnd(routes, instance, deadline):
    """
    mã giả vnd:
        khởi tạo các cấu trúc lân cận neighborhood  n1 , n2 , vvvv
        l = 1 // dùng lân cận đầu tiên
        vòng lặp(chạy đến hết các cấu trúc )
            tìm giả pháp x_new tốt nhất trong vùng lân gội nl của x
            nêu x_new tốt hơn x:
                x = x_new
                l = 1 // lại reset lại

            nếu x_new kém hơn hoặc bằng :
                l = l + 1
        trả về x
    """
    L = 1
    while L <= MAX_VND_LEVEL:
        if time.perf_counter() >= deadline:
            break
        if L == 1:
            new_routes = best_relocate(routes, instance, deadline)
        elif L == 2:
            new_routes = best_swap(routes, instance, deadline)
        else:
            new_routes = best_two_opt(routes, instance, deadline)

        if new_routes is not None:
            routes = new_routes
            L = 1
        else:
            L += 1
    return routes


def read_input():
    """
    Đọc dữ liệu từ Standard Input.
    Định dạng chuẩn:
    N K
    Ma trận khoảng cách (N+1) x (N+1)
    """
    input_data = sys.stdin.read().replace("\ufeff", "").replace("ï»¿", "").split()
    if not input_data:
        return None

    n = int(input_data[0])  # Số điểm giao hàng (không tính bưu điện 0)
    k = int(input_data[1])  # Số xe

    # Kích thước ma trận là (N+1) x (N+1) vì có thêm điểm 0
    size = n + 1
    distance = []
    idx = 2

    for _ in range(size):
        row = []
        for _ in range(size):
            row.append(float(input_data[idx]))
            idx += 1
        distance.append(row)

    return Instance(n, k, distance)


def candidate_positions(route, rng, limit=CANDIDATE_LIMIT):
    count = len(route)
    if count <= limit:
        return range(1, count + 1)

    positions = {1, count}
    step = max(1, count // 8)
    for pos in range(1, count + 1, step):
        positions.add(pos)

    while len(positions) < limit:
        positions.add(rng.randint(1, count))

    return list(positions)


def build_initial(instance, rng, deadline):
    d = instance.distance
    routes = [[0] for _ in range(instance.k)]
    lengths = [0.0] * instance.k

    points = list(range(1, instance.n + 1))
    points.sort(key=lambda p: d[0][p])
    for r_idx in range(min(instance.k, len(points))):
        point = points.pop(0)
        routes[r_idx].append(point)
        lengths[r_idx] = route_length(routes[r_idx], d)

    rng.shuffle(points)

    for point in points:
        if time.perf_counter() >= deadline:
            r_idx = min(range(instance.k), key=lambda idx: lengths[idx])
            delta = insertion_delta(
                routes[r_idx],
                point,
                len(routes[r_idx]),
                d,
            )
            routes[r_idx].append(point)
            lengths[r_idx] += delta
            continue

        best = None
        total = sum(lengths)
        order = sorted(range(instance.k), key=lambda idx: lengths[idx])

        for r_idx in order:
            route = routes[r_idx]
            other_max = max((lengths[i] for i in range(instance.k) if i != r_idx), default=0.0)

            for pos in candidate_positions(route, rng):
                delta = insertion_delta(route, point, pos, d)
                new_len = lengths[r_idx] + delta

                score = (max(other_max, new_len), total + delta, new_len)
                if best is None or score < best[0]:
                    best = (score, r_idx, pos, delta)

        if best is not None:
            _, r_idx, pos, delta = best
            routes[r_idx].insert(pos, point)
            lengths[r_idx] += delta

    return routes


def shake(routes, k, rng):
    new_routes = copy.deepcopy(routes)
    for _ in range(k):
        valid_src = [idx for idx, r in enumerate(new_routes) if len(r) > 1]
        if not valid_src:
            break
        src = rng.choice(valid_src)
        p = rng.randint(1, len(new_routes[src]) - 1)
        point = new_routes[src].pop(p)

        dst = rng.randrange(len(new_routes))
        pos = rng.randint(1, len(new_routes[dst]))
        new_routes[dst].insert(pos, point)
    return new_routes


def solve(instance, return_stats=False):
    rng = random.Random(RANDOM_SEED)
    deadline = time.perf_counter() + TIME_LIMIT
    iterations = 0
    outer_iterations = 0

    routes = build_initial(instance, rng, deadline)
    routes = vnd(routes, instance, deadline)

    best_routes = routes
    best_obj = objective_from_lengths(
        all_routes_length(routes, instance.distance)
    )

    k_max = MAX_SHAKE_LEVEL
    while time.perf_counter() < deadline:
        outer_iterations += 1
        k = 1
        while k <= k_max and time.perf_counter() < deadline:
            iterations += 1
            shaken = shake(best_routes, k, rng)
            local_opt = vnd(shaken, instance, deadline)
            local_obj = objective_from_lengths(
                all_routes_length(local_opt, instance.distance)
            )

            if local_obj < best_obj:
                best_routes = local_opt
                best_obj = local_obj
                k = 1
            else:
                k += 1

    if return_stats:
        return best_routes, {
            "iterations": iterations,
            "outer_iterations": outer_iterations,
        }
    return best_routes


def main():
    instance = read_input()
    if not instance:
        return

    best_routes = solve(instance)

    print(instance.k)
    for route in best_routes:
        print(len(route))
        print(" ".join(map(str, route)))


if __name__ == "__main__":
    main()
