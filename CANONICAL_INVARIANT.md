# Canonical v2 invariant

## Stored-value invariant

For every record marked `verified=true`:

```text
value == canonical_value
canonical_value == quantize_nearest(median(inlier raw source values), canonical_tick)
```

`canonical_tick` is an immutable feed parameter and cannot exceed one whole
declared unit (`10 ** decimals`). The contract stores the canonical value only;
the volatile raw values used during execution are not exposed as a verified
price.

## Source-status invariant

Each configured source is fetched or the entire observation fails. There are no
partially verified records. The public record includes exactly one status for
every configured source (`inlier` or `outlier`) and must satisfy:

```text
source_count == len(source_statuses)
inlier_count + outlier_count == source_count
```

Statuses are deterministically recomputed from the raw-source proof using the
feed's median and `source_deviation_bps` rule.

## Validator equivalence

The leader returns a private execution candidate containing raw source values and
a public record. A validator:

1. derives the public record again from the leader proof, rejecting any mismatch;
2. independently fetches every source and derives its own candidate; and
3. requires byte-for-byte canonical JSON equality of both public records.

Thus an alternative raw observation can only be accepted when it preserves the
same canonical value, same complete source statuses, and same counts. A
tolerance is never applied to `value` or any other stored verified field.

## Fail-closed behavior

HTTP errors, missing JSON paths, invalid decimals, source identity mismatches,
or insufficient inliers revert the observation. They cannot create a record with
`verified=true`.
