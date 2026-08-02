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
    Contract=object,
    public=_Public(),
    vm=types.SimpleNamespace(UserError=_UserError, Return=object),
    message=types.SimpleNamespace(sender_address=b""),
)
stub.TreeMap = _GenericStorage
stub.DynArray = _GenericStorage
stub.Address = bytes
stub.u256 = int
stub.__all__ = ["gl", "TreeMap", "DynArray", "Address", "u256"]
prior_genlayer = sys.modules.get("genlayer")
sys.modules["genlayer"] = stub


MODULE_PATH = Path(__file__).parents[2] / "contracts" / "QuorumFeedRegistry.py"
SPEC = importlib.util.spec_from_file_location("quorumfeed_contract", MODULE_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(module)
if prior_genlayer is None:
    del sys.modules["genlayer"]
else:
    sys.modules["genlayer"] = prior_genlayer


POLICY = {"min_sources": 2, "validator_tolerance_bps": 100, "source_deviation_bps": 300}


def _observation(a=10000, b=10100, aggregate=10050):
    return {
        "value": aggregate,
        "source_values": [{"id": "alpha", "value": a}, {"id": "beta", "value": b}],
        "source_count": 2,
        "failed_sources": [],
        "outlier_sources": [],
        "spread_bps": 50,
    }


def test_accepts_independent_values_inside_tolerance():
    assert module._equivalent_observations(
        _observation(), _observation(10020, 10120, 10070), POLICY
    )


def test_rejects_fabricated_source():
    leader = _observation()
    leader["source_values"][1]["id"] = "fabricated"
    assert not module._equivalent_observations(leader, _observation(), POLICY)


def test_rejects_value_outside_validator_tolerance():
    assert not module._equivalent_observations(
        _observation(), _observation(12000, 12100, 12050), POLICY
    )


def test_fixed_point_parser_never_uses_binary_float():
    assert module._parse_fixed("123.456789", 4) == 1234567
    assert module._parse_fixed("-0.125", 3) == -125
