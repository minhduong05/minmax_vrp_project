from scripts.run_algorithm_benchmarks import (
    Reference,
    comparison_status,
    find_reference,
    gap_percent,
    infer_base_name,
)


def test_infer_base_name_removes_k_suffix():
    assert infer_base_name("eil51_k3") == "eil51"
    assert infer_base_name("berlin52-k7") == "berlin52"
    assert infer_base_name("tc12") == "tc12"


def test_find_reference_matches_converted_instance_name():
    reference = Reference(
        dataset="mtsplib_minmax",
        instance="eil51",
        k=3,
        reference_type="main",
        max_route=159,
        total_distance=474,
        balance=3,
        return_to_depot=True,
        source="unit-test",
        source_file="",
    )
    references = {("mtsplib_minmax", "eil51", 3): reference}

    assert find_reference(references, "mtsplib_minmax", "eil51_k3", 3) == reference
    assert find_reference(references, "mtsplib_minmax", "eil51_k5", 5) is None


def test_gap_and_comparison_status():
    reference = Reference(
        dataset="hustack",
        instance="tc12",
        k=2,
        reference_type="jury",
        max_route=10,
        total_distance=19,
        balance=1,
        return_to_depot=False,
        source="unit-test",
        source_file="",
    )

    assert gap_percent(12, 10) == "20.00"
    assert comparison_status(9, 30, reference) == "better_max"
    assert comparison_status(11, 18, reference) == "worse_max"
    assert comparison_status(10, 18, reference) == "same_max_better_total"
    assert comparison_status(10, 20, reference) == "same_max_worse_total"
    assert comparison_status(10, 19, reference) == "matched"
    assert comparison_status(10, 19, None) == "no_reference"
