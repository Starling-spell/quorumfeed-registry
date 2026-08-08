# Corrected GenLayer submission

**Contribution type:** Intelligent Contracts

**Title:** QuorumFeed Canonical - Exact Validator-Agreed Oracle

**Description:**

QuorumFeed Canonical is a reusable GenLayer numeric-web oracle with an exact validator-agreed stored result. Every validator fetches every configured HTTPS JSON source, parses fixed-point values, recomputes inlier/outlier status and the inlier median, then applies an immutable bounded canonical tick. The leader proof is independently recomputed; consensus requires exact equality of the whole public record: value, canonical value, tick, source count, inlier/outlier counts and every source status. Tolerance is never used to accept an alternative stored value. Failed or missing sources revert rather than creating a partially verified record. Immutable observations, O(1) latest indexes, public-URL protections and `is_verified` make this reusable for rates, benchmarks, weather and agent policy gates. GenVM lint and 17 direct/unit tests pass. A commit-pinned live consensus proof is included.

**Evidence:**

- GitHub: https://github.com/Starling-spell/quorumfeed-registry
- Corrected v2 contract: pending deployment
- Corrected v2 live observation: pending deployment
