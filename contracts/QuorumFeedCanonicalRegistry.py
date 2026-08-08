# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json
import re
from urllib.parse import urlsplit


# QuorumFeed Canonical Registry v2 deliberately separates volatile raw API
# observations from the value that consumers are allowed to trust.  The only
# stored price is a deterministic, bounded-resolution median.  Validators must
# independently derive the *identical* public record; a tolerance is never used
# to accept an alternative verified price.
POLICY_VERSION = "quorumfeed-canonical-v2"
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
    text = str(value).strip()
    if re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", text) is None:
        raise gl.vm.UserError(f"{ERROR_EXTERNAL} source value is not a plain decimal")
    negative = text.startswith("-")
    if negative:
        text = text[1:]
    pieces = text.split(".", 1)
    whole = pieces[0]
    fraction = pieces[1] if len(pieces) == 2 else ""
    fraction = fraction[:decimals].ljust(decimals, "0")
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
    return (abs(left - right) * 10000) // max(abs(left), abs(right), 1)


def _median(values: list) -> int:
    ordered = sorted([int(value) for value in values])
    if not ordered:
        raise gl.vm.UserError(f"{ERROR_TRANSIENT} no source values")
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) // 2


def _quantize_nearest(value: int, tick: int) -> int:
    """Deterministic half-up quantization, symmetric for negative values."""
    magnitude = abs(int(value))
    quotient = magnitude // tick
    if (magnitude % tick) * 2 >= tick:
        quotient += 1
    result = quotient * tick
    return -result if value < 0 else result


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
    for pattern in (
        r"127(?:\.[0-9]{1,3}){3}", r"10(?:\.[0-9]{1,3}){3}",
        r"192\.168(?:\.[0-9]{1,3}){2}", r"169\.254(?:\.[0-9]{1,3}){2}",
    ):
        if re.fullmatch(pattern, host):
            return False
    match = re.fullmatch(r"172\.([0-9]{1,2})(?:\.[0-9]{1,3}){2}", host)
    return not (match is not None and 16 <= int(match.group(1)) <= 31)


def _validate_sources(raw_sources, min_sources: int) -> list:
    if not isinstance(raw_sources, list):
        raise gl.vm.UserError(f"{ERROR_EXPECTED} sources_json must encode a list")
    if len(raw_sources) < min_sources or len(raw_sources) > MAX_SOURCES:
        raise gl.vm.UserError(f"{ERROR_EXPECTED} invalid source count")
    result = []
    seen = {}
    for raw in raw_sources:
        if not isinstance(raw, dict):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} each source must be an object")
        source_id = _normalize_id(raw.get("id", ""), MAX_SOURCE_ID, "source id")
        if source_id in seen:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} duplicate source id")
        seen[source_id] = True
        url = _clean(raw.get("url", ""), MAX_URL)
        path = _clean(raw.get("path", ""), MAX_PATH)
        if not _is_public_https(url) or re.search(r"[\s#]", url):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} source URL must be public HTTPS")
        if not path or re.fullmatch(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*", path) is None:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} invalid JSON path")
        result.append({"id": source_id, "url": url, "path": path})
    result.sort(key=lambda item: item["id"])
    return result


def _fetch_json(source: dict):
    try:
        response = gl.nondet.web.get(
            source["url"],
            headers={"Accept": "application/json", "User-Agent": "QuorumFeedCanonical/2.0"},
        )
    except Exception:
        raise gl.vm.UserError(f"{ERROR_TRANSIENT} {source['id']} request failed")
    status = int(getattr(response, "status", 0) or 0)
    if 400 <= status < 500:
        raise gl.vm.UserError(f"{ERROR_EXTERNAL} {source['id']} returned HTTP {status}")
    if status >= 500 or status == 0:
        raise gl.vm.UserError(f"{ERROR_TRANSIENT} {source['id']} unavailable")
    body = getattr(response, "body", b"")
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="ignore")
    try:
        return json.loads(str(body))
    except Exception:
        raise gl.vm.UserError(f"{ERROR_TRANSIENT} {source['id']} returned invalid JSON")


def _fetch_proof(spec: dict) -> dict:
    # Fail closed: a verified record never reports an unchecked/missing source.
    values = []
    for source in spec["sources"]:
        data = _fetch_json(source)
        values.append({
            "id": source["id"],
            "value": _parse_fixed(_extract_path(data, source["path"]), int(spec["decimals"])),
        })
    values.sort(key=lambda item: item["id"])
    return {"raw_source_values": values}


def _derive_public(proof: dict, spec: dict) -> dict:
    """The sole canonicalization path for both leader and every validator."""
    raw_values = proof.get("raw_source_values", []) if isinstance(proof, dict) else []
    expected_ids = [source["id"] for source in spec["sources"]]
    if not isinstance(raw_values, list) or len(raw_values) != len(expected_ids):
        raise gl.vm.UserError(f"{ERROR_EXTERNAL} proof source count does not match feed")
    seen = {}
    normalized = []
    for item in raw_values:
        if not isinstance(item, dict):
            raise gl.vm.UserError(f"{ERROR_EXTERNAL} invalid proof source")
        source_id = str(item.get("id", ""))
        if source_id not in expected_ids or source_id in seen:
            raise gl.vm.UserError(f"{ERROR_EXTERNAL} proof source identity mismatch")
        value = item.get("value")
        if isinstance(value, bool):
            raise gl.vm.UserError(f"{ERROR_EXTERNAL} invalid proof value")
        try:
            normalized.append({"id": source_id, "value": int(value)})
        except Exception:
            raise gl.vm.UserError(f"{ERROR_EXTERNAL} invalid proof value")
        seen[source_id] = True
    if sorted(seen.keys()) != expected_ids:
        raise gl.vm.UserError(f"{ERROR_EXTERNAL} proof source identity mismatch")
    normalized.sort(key=lambda item: item["id"])

    raw_median = _median([item["value"] for item in normalized])
    statuses = []
    inlier_values = []
    for item in normalized:
        is_inlier = _difference_bps(item["value"], raw_median) <= int(spec["source_deviation_bps"])
        statuses.append({"id": item["id"], "status": "inlier" if is_inlier else "outlier"})
        if is_inlier:
            inlier_values.append(item["value"])
    if len(inlier_values) < int(spec["min_sources"]):
        raise gl.vm.UserError(f"{ERROR_EXTERNAL} source quorum is internally inconsistent")
    inlier_median = _median(inlier_values)
    canonical_value = _quantize_nearest(inlier_median, int(spec["canonical_tick"]))
    return {
        "value": canonical_value,
        "canonical_value": canonical_value,
        "canonical_tick": int(spec["canonical_tick"]),
        "source_count": len(normalized),
        "inlier_count": len(inlier_values),
        "outlier_count": len(normalized) - len(inlier_values),
        "source_statuses": statuses,
    }


def _validate_candidate(candidate: dict, spec: dict) -> dict:
    if not isinstance(candidate, dict):
        raise gl.vm.UserError(f"{ERROR_EXTERNAL} candidate is not an object")
    derived = _derive_public(candidate.get("proof", {}), spec)
    claimed = candidate.get("public")
    if not isinstance(claimed, dict) or json.dumps(claimed, sort_keys=True) != json.dumps(derived, sort_keys=True):
        raise gl.vm.UserError(f"{ERROR_EXTERNAL} candidate does not preserve canonical invariant")
    return derived


def _equivalent_candidates(leader: dict, validator: dict, spec: dict) -> bool:
    try:
        # This validates that each public record is the median-derived result of
        # its own raw-source proof before requiring exact public equality.
        leader_public = _validate_candidate(leader, spec)
        validator_public = _validate_candidate(validator, spec)
        return json.dumps(leader_public, sort_keys=True) == json.dumps(validator_public, sort_keys=True)
    except Exception:
        return False


class QuorumFeedCanonicalRegistry(gl.Contract):
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
        canonical_tick: int,
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
        # At most one whole unit of resolution; callers choose finer precision.
        if canonical_tick < 1 or canonical_tick > 10 ** decimals:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} canonical_tick exceeds declared precision")
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
            "canonical_tick": canonical_tick,
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
            proof = _fetch_proof(spec)
            candidate = {"proof": proof, "public": _derive_public(proof, spec)}
            return {"candidate_json": json.dumps(candidate, sort_keys=True)}

        def validator_fn(leaders_res) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            payload = leaders_res.calldata
            if not isinstance(payload, dict):
                return False
            try:
                leader = json.loads(payload.get("candidate_json", ""))
            except Exception:
                return False
            validator_proof = _fetch_proof(spec)
            validator = {
                "proof": validator_proof,
                "public": _derive_public(validator_proof, spec),
            }
            return _equivalent_candidates(leader, validator, spec)

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        try:
            candidate = json.loads(result.get("candidate_json", ""))
            return _validate_candidate(candidate, spec)
        except gl.vm.UserError:
            raise
        except Exception:
            raise gl.vm.UserError(f"{ERROR_TRANSIENT} consensus returned invalid data")

    @gl.public.write
    def observe(self, feed_id: str, observation_id: str) -> dict:
        normalized_feed = _normalize_id(feed_id, MAX_FEED_ID, "feed id")
        normalized_observation = _normalize_id(observation_id, MAX_OBSERVATION_ID, "observation id")
        if self.observation_json_by_id.get(normalized_observation, ""):
            raise gl.vm.UserError(f"{ERROR_EXPECTED} observation already exists")
        encoded_spec = self.feed_json_by_id.get(normalized_feed, "")
        if not encoded_spec:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} feed not found")
        spec = json.loads(encoded_spec)
        if spec.get("active") is not True:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} feed is inactive")
        public = self._consensus_observation(spec)
        record = {
            "observation_id": normalized_observation,
            "feed_id": normalized_feed,
            "name": spec["name"],
            "unit": spec["unit"],
            "decimals": spec["decimals"],
            "observer": str(gl.message.sender_address),
            "verified": True,
            "verification_mode": "exact-canonical-public-record",
            "policy_version": self.policy_version,
            **public,
        }
        self.observation_json_by_id[normalized_observation] = json.dumps(record, sort_keys=True)
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
        normalized_id = _normalize_id(observation_id, MAX_OBSERVATION_ID, "observation id")
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
        record = self.get_observation(observation_id)
        return bool(
            record.get("verified") is True
            and record.get("value") == record.get("canonical_value")
            and record.get("source_count") == len(record.get("source_statuses", []))
            and record.get("inlier_count", 0) + record.get("outlier_count", 0) == record.get("source_count")
        )

    @gl.public.view
    def list_feed_ids(self, offset: int, limit: int) -> list:
        if offset < 0 or limit < 1 or limit > 100:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} invalid pagination")
        return [self.feed_ids[index] for index in range(offset, min(int(self.total_feeds), offset + limit))]

    @gl.public.view
    def list_observation_ids(self, offset: int, limit: int) -> list:
        if offset < 0 or limit < 1 or limit > 100:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} invalid pagination")
        return [self.observation_ids[index] for index in range(offset, min(int(self.total_observations), offset + limit))]

    @gl.public.view
    def get_model_card(self) -> dict:
        return {
            "name": "QuorumFeed Canonical Registry",
            "policy_version": self.policy_version,
            "purpose": "Multi-source numeric web oracle with exact validator-agreed public records.",
            "consensus": (
                "Validators independently fetch every source, derive source statuses and an inlier median, "
                "quantize that median at the feed's bounded canonical tick, validate the leader proof, and "
                "require exact equality of the entire public record."
            ),
            "stored_value_invariant": "value == canonical_value == quantize(median(inlier raw values), canonical_tick)",
            "source_invariant": "source_count and every source status are recomputed and exactly agreed.",
            "consumer_gate": "is_verified",
        }
