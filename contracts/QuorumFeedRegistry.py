# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json
import re
from urllib.parse import urlsplit


POLICY_VERSION = "quorumfeed-v1"
MAX_FEED_ID = 64
MAX_OBSERVATION_ID = 96
MAX_SOURCES = 7
MAX_SOURCE_ID = 32
MAX_URL = 500
MAX_PATH = 160
MAX_DECIMALS = 18
ERROR_EXPECTED = "[EXPECTED]"
ERROR_EXTERNAL = "[EXTERNAL]"
ERROR_TRANSIENT = "[TRANSIENT]"


def _clean(value, limit: int) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _normalize_id(value: str, limit: int, label: str) -> str:
    result = _clean(value, limit).lower()
    if len(result) < 3 or re.fullmatch(r"[a-z0-9][a-z0-9._-]*", result) is None:
        raise gl.vm.UserError(f"{ERROR_EXPECTED} invalid {label}")
    return result


def _parse_fixed(value, decimals: int) -> int:
    """Convert a JSON number/string to a signed fixed-point integer without floats."""
    text = str(value).strip()
    if re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", text) is None:
        raise gl.vm.UserError(f"{ERROR_EXTERNAL} source value is not a plain decimal")
    negative = text.startswith("-")
    if negative:
        text = text[1:]
    pieces = text.split(".", 1)
    whole = pieces[0]
    fraction = pieces[1] if len(pieces) == 2 else ""
    if len(fraction) > decimals:
        fraction = fraction[:decimals]
    fraction = fraction.ljust(decimals, "0")
    scaled = int(whole) * (10 ** decimals)
    if fraction:
        scaled += int(fraction)
    return -scaled if negative else scaled


def _extract_path(data, path: str):
    current = data
    for segment in path.split("."):
        if isinstance(current, dict):
            if segment not in current:
                raise gl.vm.UserError(f"{ERROR_EXTERNAL} JSON path not found")
            current = current[segment]
        elif isinstance(current, list) and segment.isdigit():
            index = int(segment)
            if index >= len(current):
                raise gl.vm.UserError(f"{ERROR_EXTERNAL} JSON path index missing")
            current = current[index]
        else:
            raise gl.vm.UserError(f"{ERROR_EXTERNAL} JSON path not found")
    return current


def _difference_bps(left: int, right: int) -> int:
    denominator = max(abs(left), abs(right), 1)
    return (abs(left - right) * 10000) // denominator


def _is_public_https(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        host = str(parsed.hostname or "").lower()
    except Exception:
        return False
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        return False
    if host == "localhost" or host.endswith(".local") or host.endswith(".internal"):
        return False
    if re.fullmatch(r"127(?:\.[0-9]{1,3}){3}", host):
        return False
    if re.fullmatch(r"10(?:\.[0-9]{1,3}){3}", host):
        return False
    if re.fullmatch(r"192\.168(?:\.[0-9]{1,3}){2}", host):
        return False
    if re.fullmatch(r"169\.254(?:\.[0-9]{1,3}){2}", host):
        return False
    match = re.fullmatch(r"172\.([0-9]{1,2})(?:\.[0-9]{1,3}){2}", host)
    if match is not None and 16 <= int(match.group(1)) <= 31:
        return False
    return True


def _median(values: list) -> int:
    ordered = sorted(values)
    count = len(ordered)
    if count == 0:
        raise gl.vm.UserError(f"{ERROR_TRANSIENT} no source values")
    if count % 2 == 1:
        return int(ordered[count // 2])
    return (int(ordered[count // 2 - 1]) + int(ordered[count // 2])) // 2


def _validate_sources(raw_sources, min_sources: int) -> list:
    if not isinstance(raw_sources, list):
        raise gl.vm.UserError(f"{ERROR_EXPECTED} sources_json must encode a list")
    if len(raw_sources) < min_sources or len(raw_sources) > MAX_SOURCES:
        raise gl.vm.UserError(
            f"{ERROR_EXPECTED} source count must be between min_sources and {MAX_SOURCES}"
        )
    normalized = []
    seen = {}
    for raw in raw_sources:
        if not isinstance(raw, dict):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} each source must be an object")
        source_id = _normalize_id(raw.get("id", ""), MAX_SOURCE_ID, "source id")
        if source_id in seen:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} duplicate source id")
        seen[source_id] = True
        url = _clean(raw.get("url", ""), MAX_URL)
        if not _is_public_https(url) or re.search(r"[\s#]", url):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} source URL must be public HTTPS")
        path = _clean(raw.get("path", ""), MAX_PATH)
        if not path or re.fullmatch(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*", path) is None:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} invalid JSON path")
        normalized.append({"id": source_id, "url": url, "path": path})
    normalized.sort(key=lambda item: item["id"])
    return normalized


def _fetch_json(source: dict):
    label = source["id"]
    try:
        response = gl.nondet.web.get(
            source["url"],
            headers={"Accept": "application/json", "User-Agent": "QuorumFeed/1.0"},
        )
    except Exception:
        raise gl.vm.UserError(f"{ERROR_TRANSIENT} {label} request failed")
    status = int(getattr(response, "status", 0) or 0)
    if 400 <= status < 500:
        raise gl.vm.UserError(f"{ERROR_EXTERNAL} {label} returned HTTP {status}")
    if status >= 500 or status == 0:
        raise gl.vm.UserError(f"{ERROR_TRANSIENT} {label} unavailable")
    body = getattr(response, "body", b"")
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="ignore")
    try:
        return json.loads(str(body))
    except Exception:
        raise gl.vm.UserError(f"{ERROR_TRANSIENT} {label} returned invalid JSON")


def _observe_sources(spec: dict) -> dict:
    values = []
    failures = []
    decimals = int(spec["decimals"])
    for source in spec["sources"]:
        try:
            data = _fetch_json(source)
            raw_value = _extract_path(data, source["path"])
            value = _parse_fixed(raw_value, decimals)
            values.append({"id": source["id"], "value": value})
        except Exception:
            failures.append(source["id"])
    values.sort(key=lambda item: item["id"])
    failures.sort()
    if len(values) < int(spec["min_sources"]):
        raise gl.vm.UserError(f"{ERROR_TRANSIENT} insufficient live sources")

    first_median = _median([int(item["value"]) for item in values])
    inliers = []
    outliers = []
    for item in values:
        if _difference_bps(int(item["value"]), first_median) <= int(spec["source_deviation_bps"]):
            inliers.append(item)
        else:
            outliers.append(item["id"])
    if len(inliers) < int(spec["min_sources"]):
        raise gl.vm.UserError(f"{ERROR_EXTERNAL} source quorum is internally inconsistent")
    aggregate = _median([int(item["value"]) for item in inliers])
    spread_bps = 0
    for item in inliers:
        spread_bps = max(spread_bps, _difference_bps(int(item["value"]), aggregate))
    return {
        "value": aggregate,
        "source_values": inliers,
        "source_count": len(inliers),
        "failed_sources": failures,
        "outlier_sources": sorted(outliers),
        "spread_bps": spread_bps,
    }


def _equivalent_observations(leader: dict, validator: dict, spec: dict) -> bool:
    """Verify every leader datum, source quorum, and aggregate independently."""
    try:
        leader_values = leader["source_values"]
        validator_values = validator["source_values"]
        if not isinstance(leader_values, list) or not isinstance(validator_values, list):
            return False
        minimum = int(spec["min_sources"])
        if len(leader_values) < minimum or len(validator_values) < minimum:
            return False
        validator_by_id = {str(item["id"]): int(item["value"]) for item in validator_values}
        overlap = 0
        tolerance = int(spec["validator_tolerance_bps"])
        for item in leader_values:
            source_id = str(item["id"])
            if source_id not in validator_by_id:
                return False
            if _difference_bps(int(item["value"]), validator_by_id[source_id]) > tolerance:
                return False
            overlap += 1
        if overlap < minimum:
            return False
        if _difference_bps(int(leader["value"]), int(validator["value"])) > tolerance:
            return False
        if int(leader["spread_bps"]) > int(spec["source_deviation_bps"]):
            return False
        return True
    except Exception:
        return False


class QuorumFeedRegistry(gl.Contract):
    feed_json_by_id: TreeMap[str, str]
    observation_json_by_id: TreeMap[str, str]
    latest_observation_by_feed: TreeMap[str, str]
    creator_by_feed: TreeMap[str, Address]
    feed_ids: DynArray[str]
    observation_ids: DynArray[str]
    total_feeds: u256
    total_observations: u256
    policy_version: str

    def __init__(self) -> None:
        self.total_feeds = u256(0)
        self.total_observations = u256(0)
        self.policy_version = POLICY_VERSION

    @gl.public.write
    def create_feed(
        self,
        feed_id: str,
        name: str,
        unit: str,
        decimals: int,
        min_sources: int,
        source_deviation_bps: int,
        validator_tolerance_bps: int,
        sources_json: str,
    ) -> dict:
        normalized_id = _normalize_id(feed_id, MAX_FEED_ID, "feed id")
        if self.feed_json_by_id.get(normalized_id, ""):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} feed already exists")
        if decimals < 0 or decimals > MAX_DECIMALS:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} decimals must be 0-{MAX_DECIMALS}")
        if min_sources < 2 or min_sources > MAX_SOURCES:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} min_sources must be 2-{MAX_SOURCES}")
        if source_deviation_bps < 1 or source_deviation_bps > 5000:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} source deviation must be 1-5000 bps")
        if validator_tolerance_bps < 1 or validator_tolerance_bps > 1000:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} validator tolerance must be 1-1000 bps")
        try:
            decoded_sources = json.loads(sources_json)
        except Exception:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} invalid sources_json")
        sources = _validate_sources(decoded_sources, min_sources)
        spec = {
            "feed_id": normalized_id,
            "name": _clean(name, 100),
            "unit": _clean(unit, 32),
            "decimals": decimals,
            "min_sources": min_sources,
            "source_deviation_bps": source_deviation_bps,
            "validator_tolerance_bps": validator_tolerance_bps,
            "sources": sources,
            "active": True,
            "creator": str(gl.message.sender_address),
            "policy_version": self.policy_version,
        }
        if not spec["name"] or not spec["unit"]:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} name and unit are required")
        self.feed_json_by_id[normalized_id] = json.dumps(spec, sort_keys=True)
        self.creator_by_feed[normalized_id] = gl.message.sender_address
        self.feed_ids.append(normalized_id)
        self.total_feeds = u256(int(self.total_feeds) + 1)
        return spec

    def _consensus_observation(self, spec: dict) -> dict:
        def leader_fn():
            return {"observation_json": json.dumps(_observe_sources(spec), sort_keys=True)}

        def validator_fn(leaders_res) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            payload = leaders_res.calldata
            if not isinstance(payload, dict):
                return False
            try:
                leader = json.loads(payload.get("observation_json", ""))
            except Exception:
                return False
            if not isinstance(leader, dict):
                return False
            validator = _observe_sources(spec)
            return _equivalent_observations(leader, validator, spec)

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        try:
            observation = json.loads(result.get("observation_json", ""))
        except Exception:
            observation = {}
        if not isinstance(observation, dict) or not observation:
            raise gl.vm.UserError(f"{ERROR_TRANSIENT} consensus returned invalid data")
        return observation

    @gl.public.write
    def observe(self, feed_id: str, observation_id: str) -> dict:
        normalized_feed = _normalize_id(feed_id, MAX_FEED_ID, "feed id")
        normalized_observation = _normalize_id(
            observation_id, MAX_OBSERVATION_ID, "observation id"
        )
        if self.observation_json_by_id.get(normalized_observation, ""):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} observation already exists")
        encoded_spec = self.feed_json_by_id.get(normalized_feed, "")
        if not encoded_spec:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} feed not found")
        spec = json.loads(encoded_spec)
        if spec.get("active") is not True:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} feed is inactive")
        observation = self._consensus_observation(spec)
        record = {
            "observation_id": normalized_observation,
            "feed_id": normalized_feed,
            "name": spec["name"],
            "unit": spec["unit"],
            "decimals": spec["decimals"],
            "observer": str(gl.message.sender_address),
            "verified": True,
            "policy_version": self.policy_version,
            **observation,
        }
        encoded = json.dumps(record, sort_keys=True)
        self.observation_json_by_id[normalized_observation] = encoded
        self.latest_observation_by_feed[normalized_feed] = normalized_observation
        self.observation_ids.append(normalized_observation)
        self.total_observations = u256(int(self.total_observations) + 1)
        return record

    @gl.public.write
    def deactivate_feed(self, feed_id: str) -> None:
        normalized_id = _normalize_id(feed_id, MAX_FEED_ID, "feed id")
        encoded = self.feed_json_by_id.get(normalized_id, "")
        if not encoded:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} feed not found")
        if gl.message.sender_address != self.creator_by_feed[normalized_id]:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} only feed creator can deactivate")
        spec = json.loads(encoded)
        spec["active"] = False
        self.feed_json_by_id[normalized_id] = json.dumps(spec, sort_keys=True)

    @gl.public.view
    def get_feed(self, feed_id: str) -> dict:
        normalized_id = _normalize_id(feed_id, MAX_FEED_ID, "feed id")
        encoded = self.feed_json_by_id.get(normalized_id, "")
        if not encoded:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} feed not found")
        return json.loads(encoded)

    @gl.public.view
    def get_observation(self, observation_id: str) -> dict:
        normalized_id = _normalize_id(
            observation_id, MAX_OBSERVATION_ID, "observation id"
        )
        encoded = self.observation_json_by_id.get(normalized_id, "")
        if not encoded:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} observation not found")
        return json.loads(encoded)

    @gl.public.view
    def get_latest(self, feed_id: str) -> dict:
        normalized_id = _normalize_id(feed_id, MAX_FEED_ID, "feed id")
        observation_id = self.latest_observation_by_feed.get(normalized_id, "")
        if not observation_id:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} feed has no observations")
        return self.get_observation(observation_id)

    @gl.public.view
    def is_verified(self, observation_id: str) -> bool:
        return bool(self.get_observation(observation_id).get("verified") is True)

    @gl.public.view
    def list_feed_ids(self, offset: int, limit: int) -> list:
        if offset < 0 or limit < 1 or limit > 100:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} invalid pagination")
        result = []
        for index in range(offset, min(int(self.total_feeds), offset + limit)):
            result.append(self.feed_ids[index])
        return result

    @gl.public.view
    def list_observation_ids(self, offset: int, limit: int) -> list:
        if offset < 0 or limit < 1 or limit > 100:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} invalid pagination")
        result = []
        for index in range(offset, min(int(self.total_observations), offset + limit)):
            result.append(self.observation_ids[index])
        return result

    @gl.public.view
    def get_model_card(self) -> dict:
        return {
            "name": "QuorumFeed Registry",
            "policy_version": self.policy_version,
            "purpose": "Reusable multi-source numeric web oracle for contracts and agents.",
            "consensus": (
                "Each validator independently fetches every configured JSON API, "
                "normalizes values to fixed-point integers, removes bounded outliers, "
                "recomputes the median, and checks every leader source plus the aggregate."
            ),
            "security_model": "Independent source quorum nested inside GenLayer validator quorum.",
            "consumer_methods": ["get_latest", "get_observation", "is_verified"],
        }
