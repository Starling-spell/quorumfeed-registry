import json


SOURCES = [
    {"id": "alpha", "url": "https://alpha.example/quote", "path": "data.price"},
    {"id": "beta", "url": "https://beta.example/quote", "path": "price"},
    {"id": "gamma", "url": "https://gamma.example/quote", "path": "result.0.last"},
]


def _mock_quotes(direct_vm, alpha="100.00", beta="101.00", gamma="250.00"):
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
        "demo.usd",
        "Demo reference value",
        "USD",
        2,
        2,
        300,
        100,
        json.dumps(SOURCES),
    )


def test_multi_source_median_filters_outlier(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy("contracts/QuorumFeedRegistry.py")
    direct_vm.sender = direct_alice
    _create(contract)
    _mock_quotes(direct_vm)

    record = contract.observe("demo.usd", "demo.usd.sample-001")

    assert record["value"] == 10050
    assert record["source_count"] == 2
    assert record["outlier_sources"] == ["gamma"]
    assert record["verified"] is True
    assert contract.is_verified("demo.usd.sample-001") is True
    assert contract.get_latest("demo.usd")["observation_id"] == "demo.usd.sample-001"


def test_feed_spec_is_canonicalized(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy("contracts/QuorumFeedRegistry.py")
    direct_vm.sender = direct_alice
    spec = _create(contract)

    assert [source["id"] for source in spec["sources"]] == ["alpha", "beta", "gamma"]
    assert contract.list_feed_ids(0, 10) == ["demo.usd"]


def test_duplicate_observation_reverts(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy("contracts/QuorumFeedRegistry.py")
    direct_vm.sender = direct_alice
    _create(contract)
    _mock_quotes(direct_vm, gamma="100.50")
    contract.observe("demo.usd", "demo.usd.sample-001")

    with direct_vm.expect_revert("observation already exists"):
        contract.observe("demo.usd", "demo.usd.sample-001")


def test_only_creator_can_deactivate(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = direct_deploy("contracts/QuorumFeedRegistry.py")
    direct_vm.sender = direct_alice
    _create(contract)

    direct_vm.sender = direct_bob
    with direct_vm.expect_revert("only feed creator can deactivate"):
        contract.deactivate_feed("demo.usd")

    direct_vm.sender = direct_alice
    contract.deactivate_feed("demo.usd")
    assert contract.get_feed("demo.usd")["active"] is False


def test_rejects_weak_single_source_feed(direct_vm, direct_deploy, direct_alice):
    contract = direct_deploy("contracts/QuorumFeedRegistry.py")
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("min_sources must be 2-7"):
        contract.create_feed(
            "weak.feed", "Weak", "USD", 2, 1, 100, 50, json.dumps(SOURCES[:1])
        )

