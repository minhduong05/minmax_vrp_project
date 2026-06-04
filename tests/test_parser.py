import pytest

from parser import load_instance


def test_load_tsp_raw_requires_k(tmp_path):
    path = tmp_path / "tiny.tsp"
    path.write_text(
        "\n".join(
            [
                "NAME: tiny",
                "TYPE: TSP",
                "DIMENSION: 3",
                "EDGE_WEIGHT_TYPE: EUC_2D",
                "NODE_COORD_SECTION",
                "1 0 0",
                "2 3 4",
                "3 6 8",
                "EOF",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="K is required"):
        load_instance(path)


def test_load_tsp_raw_with_real_distances(tmp_path):
    path = tmp_path / "tiny.tsp"
    path.write_text(
        "\n".join(
            [
                "NAME: tiny",
                "TYPE: TSP",
                "DIMENSION: 3",
                "EDGE_WEIGHT_TYPE: EUC_2D",
                "NODE_COORD_SECTION",
                "1 0 0",
                "2 3 4",
                "3 6 8",
                "EOF",
            ]
        ),
        encoding="utf-8",
    )

    instance = load_instance(path, k=2)

    assert instance.n == 2
    assert instance.k == 2
    assert instance.distance[0][1] == 5.0
    assert instance.distance[0][2] == 10.0
    assert instance.distance[1][2] == 5.0
