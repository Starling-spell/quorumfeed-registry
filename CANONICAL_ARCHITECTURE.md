# Canonical v2 architecture

## Trust boundary

External HTTPS APIs own raw numeric facts. QuorumFeed Canonical owns the
consensus-critical state transition: the immutable canonical value and exact
source-status record. A UI or indexer may display data but cannot create a
verified observation.

## Consensus flow

`create_feed` fixes sources, precision, outlier rule and canonical tick.
`observe` fetches every source, converts each value to a fixed-point integer,
classifies inliers against the raw median, and derives:

```text
canonical_value = quantize_nearest(median(inlier values), canonical_tick)
```

The leader supplies a raw-source proof and the public record derived from it.
Each validator independently recomputes the leader record, fetches every source
again, derives its own record, and requires canonical JSON equality of the two
public records.

## Exact stored fields

The exact-equality comparison covers the stored value, canonical value, tick,
source count, inlier count, outlier count and every `{id, status}` pair. This
binds the reported source fields to recomputation and prevents alternate verified
results. The leader’s `value` must equal the median-derived canonical value from
its own proof before a validator considers it.

## Fail-closed rules

- every configured source must return a parseable value;
- every proof source must match the immutable feed identity exactly once;
- at least `min_sources` must be inliers;
- any missing source, HTTP error, invalid path/value, proof mismatch or public
  record mismatch reverts; and
- no tolerance is applied to any stored verified field.

The outlier tolerance only classifies a source within a candidate; it cannot make
two different `value` fields validator-compatible.
