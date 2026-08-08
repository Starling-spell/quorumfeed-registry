import importlib.util
import sys
import types
from pathlib import Path


class _GenericStorage:
    @classmethod
    def __class_getitem__(cls, _item):
        return cls


class _Public:
    @staticmethod
    def write(function):
        return function

    @staticmethod
    def view(function):
        return function


class _UserError(Exception):
    pass


stub = types.ModuleType("genlayer")
stub.gl = types.SimpleNamespace(
    Contract=object, public=_Public(),
    vm=types.SimpleNamespace(UserError=_UserError, Return=object),
    message=types.SimpleNamespace(sender_address=b""),
)
stub.TreeMap = _GenericStorage
stub.DynArray = _GenericStorage
stub.Address = bytes
stub.u256 = int
stub.__all__ = ["gl", "TreeMap", "DynArray", "Address", "u256"]
prior = sys.modules.get("genlayer")
sys.modules["genlayer"] = stub
path = Path(__file__).parents[2] / "contracts" / "QuorumFeedCanonicalRegistry.py"
spec = importlib.util.spec_from_file_location("quorumfeed_canonical_contract", path)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
if prior is None:
    del sys.modules["genlayer"]
else:
    sys.modules["genlayer"] = prior


POLICY = {
    "sources": [{"id": "alpha"}, {"id": "beta"}, {"id": "gamma"}],
    "decimals": 2,
    "min_sources": 2,
    "source_deviation_bps": 300,
    "canonical_tick": 100,
}


def _candidate(alpha=10021, beta=10079, gamma=15000):
    proof = {"raw_source_values": [
        {"id": "alpha", "value": alpha},
        {"id": "beta", "value": beta},
        {"id": "gamma", "value": gamma},
    ]}
    return {"proof": proof, "public": module._derive_public(proof, POLICY)}


def test_candidate_value_is_recomputed_from_its_own_median_proof():
    candidate = _candidate()
    candidate["public"]["value"] = 999999
    assert not module._equivalent_candidates(candidate, _candidate(), POLICY)


def test_exact_canonical_value_is_required_even_when_raw_values_are_close():
    leader = _candidate(10021, 10079, 15000)
    validator = _candidate(10025, 10075, 15010)
    assert module._equivalent_candidates(leader, validator, POLICY)
    validator["proof"]["raw_source_values"][0]["value"] = 10300
    validator["proof"]["raw_source_values"][1]["value"] = 10350
    validator["public"] = module._derive_public(validator["proof"], POLICY)
    assert not module._equivalent_candidates(leader, validator, POLICY)


def test_source_statuses_and_counts_are_bound_to_recomputation():
    candidate = _candidate()
    candidate["public"]["source_count"] = 2
    assert not module._equivalent_candidates(candidate, _candidate(), POLICY)
    candidate = _candidate()
    candidate["public"]["source_statuses"][2]["status"] = "inlier"
    assert not module._equivalent_candidates(candidate, _candidate(), POLICY)


def test_quantization_is_symmetric_and_bounded():
    assert module._quantize_nearest(10050, 100) == 10100
    assert module._quantize_nearest(-10050, 100) == -10100
