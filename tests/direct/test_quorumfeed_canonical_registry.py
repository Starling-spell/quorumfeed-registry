import json


SOURCES = [
    {"id": "alpha", "url": "https://alpha.example/quote", "path": "data.price"},
    {"id": "beta", "url": "https://beta.example/quote", "path": "price"},
    {"id": "gamma", "url": "https://gamma.example/quote", "path": "result.0.last"},
]


def _mock_quotes(direct_vm, alpha="100.21", beta="100.79", gamma="150.00"):
    direct_vm.mock_web(
        r".*alpha\.example/quote.*",
        {"status": 200, "body": json.dumps({"data": {"price": alpha}})},
    )
    direct_vm.mock_web(
        r".*beta\.example/quote.*",
        {"status": 200, "body": json.dumps({"price": beta})},
    )
    direct_vm.mock_web(
        r".*gamma\.example/quote.*",
        {"status": 200, "body": json.dumps({"result": [{"last": gamma}]})},
    )


def _create(contract):
    return contract.create_feed(
        "demo.usd.canonical", "Demo canonical value", "USD", 2, 2, 300, 100,
        json.dumps(SOURCES),
    )


def test_verified_value_is_exact_canonical_median(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy("contracts/QuorumFeedCanonicalRegistry.py")
    direct_vm.sender = direct_alice
    _create(contract)
    _mock_quotes(direct_vm)

    record = contract.observe("demo.usd.canonical", "demo.usd.canonical.001")

    # Raw inlier median = 10050 cents; canonical tick = 100 cents; stored = 10100.
    assert record["value"] == 10100
    assert record["canonical_value"] == 10100
    assert record["canonical_tick"] == 100
    assert record["source_count"] == 3
    assert record["inlier_count"] == 2
    assert record["outlier_count"] == 1
    assert record["source_statuses"] == [
        {"id": "alpha", "status": "inlier"},
        {"id": "beta", "status": "inlier"},
        {"id": "gamma", "status": "outlier"},
    ]
    assert contract.is_verified("demo.usd.canonical.001") is True


def test_fails_closed_when_any_configured_source_is_unavailable(
    direct_vm, direct_deploy, direct_alice
):
    contract = direct_deploy("contracts/QuorumFeedCanonicalRegistry.py")
    direct_vm.sender = direct_alice
    _create(contract)
    direct_vm.mock_web(
        r".*alpha\.example/quote.*",
        {"status": 200, "body": json.dumps({"data": {"price": "100.00"}})},
    )
    direct_vm.mock_web(
        r".*beta\.example/quote.*",
        {"status": 503, "body": "{}"},
    )
    direct_vm.mock_web(
        r".*gamma\.example/quote.*",
        {"status": 200, "body": json.dumps({"result": [{"last": "100.00"}]})},
    )

    with direct_vm.expect_revert("beta unavailable"):
        contract.observe("demo.usd.canonical", "demo.usd.canonical.002")


def test_canonical_tick_is_bounded_by_declared_precision(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy("contracts/QuorumFeedCanonicalRegistry.py")
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("canonical_tick exceeds declared precision"):
        contract.create_feed(
            "bad.tick", "Bad tick", "USD", 2, 2, 300, 101, json.dumps(SOURCES)
        )


def test_duplicate_observation_reverts(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy("contracts/QuorumFeedCanonicalRegistry.py")
    direct_vm.sender = direct_alice
    _create(contract)
    _mock_quotes(direct_vm, gamma="100.50")
    contract.observe("demo.usd.canonical", "demo.usd.canonical.003")
    with direct_vm.expect_revert("observation already exists"):
        contract.observe("demo.usd.canonical", "demo.usd.canonical.003")
