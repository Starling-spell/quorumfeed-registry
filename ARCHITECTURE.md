# Architecture and trust boundary

## Why GenLayer is central

A normal contract cannot synchronously read independent web APIs, and a single
backend oracle becomes a trusted operator. QuorumFeed nests two quorums:

1. **Source quorum:** multiple independently operated JSON APIs must agree after
   fixed-point normalization and bounded outlier filtering.
2. **Validator quorum:** every GenLayer validator re-fetches those APIs and
   verifies every source claimed by the leader plus the final aggregate.

The accepted state transition is the immutable observation. A frontend may
display or index observations, but it cannot create a verified value itself.

## Flow

`create_feed` → canonical source specification → `observe` → leader fetches all
sources → fixed-point conversion → median/outlier filtering → validators repeat
the full process → field-level tolerance checks → verified observation stored →
downstream contracts call `get_latest` or `is_verified`.

## Equivalence rule

Validators do not check formatting alone. For acceptance they require:

- both leader and validator independently reach `min_sources`;
- every source claimed by the leader also exists in the validator fetch;
- every overlapping fixed-point value is within `validator_tolerance_bps`;
- the independently computed aggregates are within the same tolerance; and
- the leader's retained-source spread respects `source_deviation_bps`.

This permits honest movement between sequential live requests while rejecting
fabricated sources, stale values, single-source observations, and implausible
aggregates.

## State design

Feed specifications are immutable except for creator-controlled deactivation.
Observations are immutable and globally keyed. O(1) indexes expose the latest
observation per feed, feed creator, and ID pagination without collection scans.

## Security limits

- At least two sources are mandatory; up to seven are supported.
- Only HTTPS endpoints are accepted, and obvious loopback/private hosts and
  credential-bearing URLs are rejected.
- Decimal conversion uses integer string parsing rather than binary floats.
- Consumers still choose appropriate sources and tolerances for their risk.
- An observation proves agreement at transaction time; consumers should enforce
  application-specific recency using transaction/block metadata.
