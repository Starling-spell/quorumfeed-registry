# GenLayer Portal submission

**Contribution type:** Intelligent Contracts

**Title:** QuorumFeed — Multi-Source Consensus Oracle Primitive

**Description:**

QuorumFeed is a reusable GenLayer primitive that turns independent public JSON APIs into consensus-verified fixed-point observations. Feed creators declare 2–7 HTTPS sources, JSON paths, precision, quorum, outlier bounds and validator tolerances. The leader fetches all sources, parses decimals without binary floats, removes bounded outliers and derives a median. Every validator independently re-fetches each API, recomputes the result, verifies every source claimed by the leader and checks the aggregate within explicit basis-point tolerances. This is substantive verification, not an LLM or format-only check. Immutable observations, O(1) latest-feed indexes, creator deactivation, public-URL protections and an `is_verified` consumer gate make it reusable for rates, benchmarks, weather and other numeric web facts. GenVM lint and all 9 tests pass. A live BTC/USD observation finalized with majority agreement and is stored verified on StudioNet.

**Evidence:**

- GitHub: https://github.com/Starling-spell/quorumfeed-registry
- Contract: https://explorer-studio.genlayer.com/address/0x744eC062010c4Bf912A482D4ba9E344B2f055e23
- Deployment: https://explorer-studio.genlayer.com/tx/0xca0a162739c3256d41003ea0925b4a6d1e54ddf9734dfefa26b1048f24248d91
- Live observation: https://explorer-studio.genlayer.com/tx/0x1bbca0101a06aff11b5ee8be682419a97d4f5b32cce685aadc2509c05828212e
