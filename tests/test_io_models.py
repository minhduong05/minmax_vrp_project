from minmax_vrp.io import read_instance
from minmax_vrp.models import Solution


def test_read_instance_and_evaluate_open_routes_by_default(tmp_path):
    input_path = tmp_path / "tiny.txt"
    input_path.write_text(
        "\n".join(
            [
                "3 2",
                "0 2 9 10",
                "2 0 3 4",
                "9 3 0 5",
                "10 4 5 0",
            ]
        ),
        encoding="utf-8",
    )

    instance = read_instance(input_path)
    solution = Solution([[0, 1, 3], [0, 2]])

    assert instance.n == 3
    assert instance.k == 2
    assert solution.is_feasible(instance)
    assert solution.route_lengths(instance) == [6, 9]
    assert solution.evaluate(instance).as_tuple() == (9, 3, 15)


def test_read_instance_preserves_real_distances(tmp_path):
    input_path = tmp_path / "real.txt"
    input_path.write_text(
        "\n".join(
            [
                "2 1",
                "0 1.5 2.25",
                "1.5 0 3.75",
                "2.25 3.75 0",
            ]
        ),
        encoding="utf-8",
    )

    instance = read_instance(input_path)
    solution = Solution([[0, 1, 2]])

    lengths = solution.route_lengths(instance)
    objective = solution.evaluate(instance)

    assert solution.is_feasible(instance)
    assert lengths == [5.25]
    assert objective.max_route_length == max(lengths)
    assert objective.total_distance == sum(lengths)
    assert objective.balance == max(lengths) - min(lengths)
