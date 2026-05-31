import math
import random
import sys
import time
from array import array


# Adjust this if the judge gives a very different time limit.
TIME_LIMIT_SECONDS = 3.8
RANDOM_SEED = 99


class Instance:
    def __init__(self, n, k, distance):
        self.n = n
        self.k = k
        self.distance = distance


class Evaluation:
    def __init__(self, max_route_length, total_distance, balance):
        self.max_route_length = max_route_length
        self.total_distance = total_distance
        self.balance = balance


class Solution:
    def __init__(self, routes):
        self.routes = routes

    def copy(self) -> "Solution":
        return Solution([route[:] for route in self.routes])

    def route_length(self, route, d):
        length = 0
        for i in range(len(route) - 1):
            length += d[route[i]][route[i + 1]]
        return length

    def route_lengths(self, instance):
        d = instance.distance
        return [self.route_length(route, d) for route in self.routes]

    def evaluate(self, instance):
        lengths = self.route_lengths(instance)
        max_len = max(lengths) if lengths else 0
        min_len = min(lengths) if lengths else 0
        return Evaluation(max_len, sum(lengths), max_len - min_len)

    def all_pickup_points(self):
        points = []
        for route in self.routes:
            points.extend(route[1:])
        return points


def read_instance_from_stdin():
    first = sys.stdin.buffer.readline().split()
    while not first:
        first = sys.stdin.buffer.readline().split()
    if len(first) < 2:
        raise ValueError("input must start with N K")
    n = int(first[0])
    k = int(first[1])
    size = n + 1
    distance = []
    for i in range(size):
        row = []
        while len(row) < size:
            row.extend(int(token) for token in sys.stdin.buffer.readline().split())
        distance.append(array("q", row[:size]))
    return Instance(n, k, distance)


def format_solution(solution):
    lines = [str(len(solution.routes))]
    for route in solution.routes:
        lines.append(str(len(route)))
        lines.append(" ".join(str(x) for x in route))
    return "\n".join(lines)


def better(a, b, instance):
    ea = a.evaluate(instance)
    eb = b.evaluate(instance)
    if ea.max_route_length != eb.max_route_length:
        return ea.max_route_length < eb.max_route_length
    if ea.total_distance != eb.total_distance:
        return ea.total_distance < eb.total_distance
    return ea.balance < eb.balance


def insertion_delta(route, point, position, instance):
    d = instance.distance
    prev_node = route[position - 1]
    if position == len(route):
        return d[prev_node][point]
    next_node = route[position]
    return d[prev_node][point] + d[point][next_node] - d[prev_node][next_node]


def removal_saving(route, position, instance):
    d = instance.distance
    node = route[position]
    prev_node = route[position - 1]
    if position == len(route) - 1:
        return d[prev_node][node]
    next_node = route[position + 1]
    return d[prev_node][node] + d[node][next_node] - d[prev_node][next_node]


def route_order_by_length(lengths, reverse):
    order = list(range(len(lengths)))
    order.sort(key=lambda idx: lengths[idx], reverse=reverse)
    return order


def candidate_positions(route, rng, limit=0):
    positions_count = len(route)
    if limit <= 0 or positions_count <= limit:
        return range(1, positions_count + 1)
    positions = {1, positions_count}
    step = max(1, positions_count // 8)
    for pos in range(1, positions_count + 1, step):
        positions.add(pos)
    while len(positions) < limit:
        positions.add(rng.randint(1, positions_count))
    return list(positions)


def build_initial(instance, rng, deadline):
    routes = [[0] for _ in range(instance.k)]
    lengths = [0] * instance.k
    d = instance.distance
    points = list(range(1, instance.n + 1))

    points.sort(key=lambda p: d[0][p])
    for r_idx in range(min(instance.k, len(points))):
        point = points.pop(0)
        routes[r_idx].append(point)
        lengths[r_idx] = d[0][point]

    # Insert remaining points one-by-one, evaluating every route and position.
    rng.shuffle(points)

    for point in points[:]:
        if time.perf_counter() >= deadline:
            break
        best = None
        route_order = route_order_by_length(lengths, reverse=False)
        total = sum(lengths)
        for r_idx in route_order:
            route = routes[r_idx]
            other_max = 0
            for idx, length in enumerate(lengths):
                if idx != r_idx and length > other_max:
                    other_max = length
            for pos in candidate_positions(route, rng):
                delta = insertion_delta(route, point, pos, instance)
                new_len = lengths[r_idx] + delta
                score = (max(other_max, new_len), total + delta, new_len)
                if best is None or score < best[0]:
                    best = (score, r_idx, pos, delta)
        if best is None:
            r_idx = min(range(instance.k), key=lambda idx: lengths[idx])
            pos = len(routes[r_idx])
            delta = d[routes[r_idx][-1]][point]
        else:
            _, r_idx, pos, delta = best
        routes[r_idx].insert(pos, point)
        lengths[r_idx] += delta

    assigned = set()
    for route in routes:
        assigned.update(route[1:])
    for point in range(1, instance.n + 1):
        if point in assigned:
            continue
        r_idx = min(range(instance.k), key=lambda idx: lengths[idx])
        delta = d[routes[r_idx][-1]][point]
        routes[r_idx].append(point)
        lengths[r_idx] += delta

    return Solution(routes)


def remove_points(solution, removed_set):
    for r_idx, route in enumerate(solution.routes):
        if len(route) <= 1:
            continue
        kept = [0]
        for point in route[1:]:
            if point not in removed_set:
                kept.append(point)
        solution.routes[r_idx] = kept


def destroy_random(solution, instance, q, rng):
    partial = solution.copy()
    points = partial.all_pickup_points()
    removed = rng.sample(points, min(q, len(points)))
    remove_points(partial, set(removed))
    return partial, removed


def destroy_route(solution, instance, q, rng):
    partial = solution.copy()
    lengths = partial.route_lengths(instance)
    non_empty = [idx for idx, route in enumerate(partial.routes) if len(route) > 1]
    if not non_empty:
        return partial, []
    if rng.random() < 0.75:
        r_idx = max(non_empty, key=lambda idx: lengths[idx])
    else:
        r_idx = rng.choice(non_empty)
    points = partial.routes[r_idx][1:]
    removed = rng.sample(points, min(q, len(points)))
    removed_set = set(removed)
    partial.routes[r_idx] = [0] + [p for p in points if p not in removed_set]
    rng.shuffle(removed)
    return partial, removed


def destroy_worst_longest(solution, instance, q, rng):
    partial = solution.copy()
    removed = []
    while len(removed) < q:
        lengths = partial.route_lengths(instance)
        non_empty = [idx for idx, route in enumerate(partial.routes) if len(route) > 1]
        if not non_empty:
            break
        r_idx = max(non_empty, key=lambda idx: lengths[idx])
        route = partial.routes[r_idx]
        candidates = []
        for pos in range(1, len(route)):
            saving = removal_saving(route, pos, instance)
            noisy = saving * (1.0 + rng.uniform(-0.15, 0.15))
            candidates.append((noisy, pos))
        candidates.sort(reverse=True)
        take = min(q - len(removed), max(1, len(candidates) // 4), len(candidates))
        positions = sorted([pos for _, pos in candidates[:take]], reverse=True)
        for pos in positions:
            removed.append(route.pop(pos))
    rng.shuffle(removed)
    return partial, removed


def destroy_related(solution, instance, q, rng):
    partial = solution.copy()
    points = partial.all_pickup_points()
    if not points:
        return partial, []
    seed = rng.choice(points)
    d = instance.distance
    ordered = points[:]
    ordered.sort(key=lambda p: d[seed][p])
    removed = [seed]
    idx = 1
    while len(removed) < min(q, len(points)) and idx < len(ordered):
        if rng.random() < 0.85:
            removed.append(ordered[idx])
        else:
            removed.append(rng.choice(ordered[idx:]))
        idx += 1
    remove_points(partial, set(removed))
    rng.shuffle(removed)
    return partial, removed


def append_remaining_fast(solution, unassigned, lengths, instance):
    d = instance.distance
    for point in unassigned[:]:
        r_idx = min(range(instance.k), key=lambda idx: lengths[idx])
        route = solution.routes[r_idx]
        best_pos = len(route)
        best_delta = d[route[-1]][point]
        for pos in range(1, len(route)):
            delta = insertion_delta(route, point, pos, instance)
            if delta < best_delta:
                best_delta = delta
                best_pos = pos
        route.insert(best_pos, point)
        lengths[r_idx] += best_delta
        unassigned.remove(point)


def repair_balanced(partial, removed, instance, rng, deadline):
    solution = partial.copy()
    unassigned = removed[:]
    rng.shuffle(unassigned)
    lengths = solution.route_lengths(instance)
    total = sum(lengths)

    while unassigned and time.perf_counter() < deadline:
        best = None
        best_point = None
        route_order = route_order_by_length(lengths, reverse=False)
        for point in unassigned:
            if time.perf_counter() >= deadline:
                break
            for r_idx in route_order:
                route = solution.routes[r_idx]
                other_max = 0
                for idx, length in enumerate(lengths):
                    if idx != r_idx and length > other_max:
                        other_max = length
                for pos in candidate_positions(route, rng):
                    delta = insertion_delta(route, point, pos, instance)
                    new_len = lengths[r_idx] + delta
                    new_total = total + delta
                    score = (max(other_max, new_len), new_total, delta)
                    if best is None or score < best[0]:
                        best = (score, r_idx, pos, delta)
                        best_point = point
        if best is None:
            point = unassigned[0]
            r_idx = min(range(instance.k), key=lambda idx: lengths[idx])
            pos = len(solution.routes[r_idx])
            delta = instance.distance[solution.routes[r_idx][-1]][point]
            best_point = point
        else:
            _, r_idx, pos, delta = best
        solution.routes[r_idx].insert(pos, best_point)
        lengths[r_idx] += delta
        total += delta
        unassigned.remove(best_point)
    if unassigned:
        append_remaining_fast(solution, unassigned, lengths, instance)
    return solution


def best_insertions_for_point(solution, lengths, total, point, instance):
    choices = []
    for r_idx, route in enumerate(solution.routes):
        other_max = 0
        for idx, length in enumerate(lengths):
            if idx != r_idx and length > other_max:
                other_max = length
        for pos in range(1, len(route) + 1):
            delta = insertion_delta(route, point, pos, instance)
            new_len = lengths[r_idx] + delta
            choices.append(((max(other_max, new_len), total + delta, delta), r_idx, pos, delta))
    choices.sort(key=lambda item: item[0])
    return choices


def repair_regret(partial, removed, instance, rng, deadline):
    solution = partial.copy()
    unassigned = removed[:]
    rng.shuffle(unassigned)
    lengths = solution.route_lengths(instance)
    total = sum(lengths)

    while unassigned and time.perf_counter() < deadline:
        selected = None
        selected_choice = None
        for point in unassigned:
            if time.perf_counter() >= deadline:
                break
            choices = best_insertions_for_point(solution, lengths, total, point, instance)
            best = choices[0]
            second = choices[1] if len(choices) > 1 else best
            regret = second[0][0] - best[0][0]
            secondary = second[0][1] - best[0][1]
            score = (regret, secondary, -best[0][0], -best[0][1])
            if selected is None or score > selected:
                selected = score
                selected_choice = (point, best)
        if selected_choice is None:
            break
        point, choice = selected_choice
        _, r_idx, pos, delta = choice
        solution.routes[r_idx].insert(pos, point)
        lengths[r_idx] += delta
        total += delta
        unassigned.remove(point)
    if unassigned:
        append_remaining_fast(solution, unassigned, lengths, instance)
    return solution


def local_search(solution, instance, rng, deadline):
    best = solution.copy()
    lengths = best.route_lengths(instance)
    if not lengths:
        return best

    longest = max(range(len(lengths)), key=lambda idx: lengths[idx])
    route = best.routes[longest]
    positions = list(range(1, len(route)))
    rng.shuffle(positions)

    for pos in positions[:30]:
        if time.perf_counter() >= deadline:
            break
        if pos >= len(route):
            continue
        point = route[pos]
        temp = best.copy()
        temp.routes[longest].pop(pos)
        temp_lengths = temp.route_lengths(instance)
        route_order = route_order_by_length(temp_lengths, reverse=False)
        for r_idx in route_order[: min(instance.k, 25)]:
            for insert_pos in candidate_positions(temp.routes[r_idx], rng):
                cand = temp.copy()
                cand.routes[r_idx].insert(insert_pos, point)
                if better(cand, best, instance):
                    best = cand
                    lengths = best.route_lengths(instance)
                    longest = max(range(len(lengths)), key=lambda idx: lengths[idx])
                    route = best.routes[longest]

    lengths = best.route_lengths(instance)
    longest = max(range(len(lengths)), key=lambda idx: lengths[idx])
    long_positions = list(range(1, len(best.routes[longest])))
    rng.shuffle(long_positions)
    other_routes = [idx for idx, route in enumerate(best.routes) if idx != longest and len(route) > 1]
    other_routes.sort(key=lambda idx: lengths[idx])
    for pos_a in long_positions[:20]:
        if time.perf_counter() >= deadline:
            break
        for r_idx in other_routes[: min(20, len(other_routes))]:
            if time.perf_counter() >= deadline:
                break
            positions_b = list(range(1, len(best.routes[r_idx])))
            rng.shuffle(positions_b)
            for pos_b in positions_b[:20]:
                if time.perf_counter() >= deadline:
                    break
                cand = best.copy()
                cand.routes[longest][pos_a], cand.routes[r_idx][pos_b] = (
                    cand.routes[r_idx][pos_b],
                    cand.routes[longest][pos_a],
                )
                if better(cand, best, instance):
                    best = cand

    lengths = best.route_lengths(instance)
    route_order = route_order_by_length(lengths, reverse=True)[: min(3, len(lengths))]
    for r_idx in route_order:
        route = best.routes[r_idx]
        m = len(route)
        if m <= 4:
            continue
        for _ in range(60):
            if time.perf_counter() >= deadline:
                break
            i = rng.randint(1, m - 2)
            j = rng.randint(i + 1, m - 1)
            cand = best.copy()
            cand.routes[r_idx][i : j + 1] = reversed(cand.routes[r_idx][i : j + 1])
            if better(cand, best, instance):
                best = cand
    return best


def scalar_value(solution, instance):
    ev = solution.evaluate(instance)
    return ev.max_route_length + 1e-6 * ev.total_distance


def solve(instance):
    rng = random.Random(RANDOM_SEED)
    start = time.perf_counter()
    deadline = start + TIME_LIMIT_SECONDS

    current = build_initial(instance, rng, deadline)
    best = current.copy()
    temperature = max(1000.0, 0.05 * max(1, best.evaluate(instance).max_route_length))

    destroy_ops = [destroy_random, destroy_route, destroy_worst_longest, destroy_related]
    repair_ops = [repair_balanced, repair_regret]
    q_min = max(1, min(int(0.05 * instance.n), 6))
    q_max = max(q_min, min(int(0.20 * instance.n), 24))

    while time.perf_counter() < deadline:
        destroy = rng.choice(destroy_ops)
        q = rng.randint(q_min, q_max) if instance.n > 0 else 0
        partial, removed = destroy(current, instance, q, rng)
        if not removed:
            continue

        repair = rng.choice(repair_ops)
        candidate = repair(partial, removed, instance, rng, deadline)
        if False:
            candidate = local_search(candidate, instance, rng, deadline)

        cur_value = scalar_value(current, instance)
        cand_value = scalar_value(candidate, instance)
        if cand_value <= cur_value:
            current = candidate
        else:
            prob = math.exp(-(cand_value - cur_value) / max(temperature, 1e-6))
            if rng.random() < prob:
                current = candidate
        temperature = max(1e-6, temperature * 0.999)

        if better(candidate, best, instance):
            best = candidate.copy()

    return best


def fallback_solution(instance):
    routes = [[0] for _ in range(instance.k)]
    for idx in range(1, instance.n + 1):
        routes[(idx - 1) % instance.k].append(idx)
    return Solution(routes)


def normalize_solution(solution, instance):
    seen = [False] * (instance.n + 1)
    routes = []
    for route in solution.routes[: instance.k]:
        new_route = [0]
        for point in route[1:]:
            if 1 <= point <= instance.n and not seen[point]:
                seen[point] = True
                new_route.append(point)
        routes.append(new_route)
    while len(routes) < instance.k:
        routes.append([0])

    lengths = Solution(routes).route_lengths(instance)
    missing = [point for point in range(1, instance.n + 1) if not seen[point]]
    for point in missing:
        best = None
        for r_idx, route in enumerate(routes):
            for pos in range(1, len(route) + 1):
                delta = insertion_delta(route, point, pos, instance)
                new_len = lengths[r_idx] + delta
                other_max = 0
                for idx, length in enumerate(lengths):
                    if idx != r_idx and length > other_max:
                        other_max = length
                score = (max(other_max, new_len), delta)
                if best is None or score < best[0]:
                    best = (score, r_idx, pos, delta)
        _, r_idx, pos, delta = best
        routes[r_idx].insert(pos, point)
        lengths[r_idx] += delta
    return Solution(routes)


def main():
    instance = read_instance_from_stdin()
    try:
        solution = solve(instance)
    except Exception:
        solution = fallback_solution(instance)
    solution = normalize_solution(solution, instance)
    sys.stdout.write(format_solution(solution))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
