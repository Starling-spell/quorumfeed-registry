# Corrected GenLayer submission

**Contribution type:** Intelligent Contracts

**Title:** QuorumFeed Canonical - Exact Validator-Agreed Oracle

**Description:**

QuorumFeed Canonical is a reusable GenLayer numeric-web oracle with an exact validator-agreed stored result. Every validator fetches every configured HTTPS JSON source, parses fixed-point values, recomputes inlier/outlier status and the inlier median, then applies an immutable bounded canonical tick. The leader proof is independently recomputed; consensus requires exact equality of the whole public record: value, canonical value, tick, source count, inlier/outlier counts and every source status. Tolerance is never used to accept an alternative stored value. Failed or missing sources revert rather than creating a partially verified record. Immutable observations, O(1) latest indexes, public-URL protections and `is_verified` make this reusable for rates, benchmarks, weather and agent policy gates. GenVM lint and 17 direct/unit tests pass. A commit-pinned live consensus proof is included.

**Evidence:**

- GitHub: https://github.com/Starling-spell/quorumfeed-registry
- Corrected v2 contract: https://explorer-studio.genlayer.com/address/0x6Fd6ACA146cBAa99088C92D8AAEe01f6b20A6cb6
- Corrected v2 deployment: https://explorer-studio.genlayer.com/tx/0x3bcb70c516c94a78109d7650227c70ce412888a1a8c642501f18543e5356300a
- Corrected v2 live observation: https://explorer-studio.genlayer.com/tx/0x5f1a47adc087482f86890381eeeac887bb07772ab43c4db0f09ffb9a0347f083
