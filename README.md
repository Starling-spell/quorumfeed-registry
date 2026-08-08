# QuorumFeed Canonical Registry

QuorumFeed Canonical is a reusable GenLayer primitive for turning several public
numeric JSON feeds into one **exact validator-agreed** fixed-point observation. It is designed
for autonomous agents and contracts that need exchange rates, commodity values,
weather measurements, benchmark metrics, or other web-native numeric facts
without trusting one API or one validator.

## Canonical v2: exact public oracle result

This v2 contract replaces the earlier tolerance-only implementation. Each
validator independently re-fetches **every** configured source, recomputes
inlier/outlier status and the inlier median, then quantizes it at a bounded
canonical tick. Consensus requires exact equality of the entire stored public
record: `value`, `canonical_value`, tick, source count, inlier/outlier counts,
and every source status. Raw API values are proof-only and are never stored as a
verified oracle value. There is no LLM and no format-only validation.

## Consumer interface

- `create_feed(...)`: register an immutable declarative feed specification.
- `observe(feed_id, observation_id)`: create a validator-verified observation.
- `get_latest(feed_id)`: read the latest verified record.
- `get_observation(observation_id)`: read an immutable historical record.
- `is_verified(observation_id)`: minimal composable consumer gate.
- `deactivate_feed(feed_id)`: creator safety switch; history remains available.

Each source specifies an HTTPS URL and a dotted JSON path. Array indexes are
supported as numeric path segments. Values are converted to fixed-point integers
at the feed's declared decimal precision. `canonical_tick` must be no larger
than one whole declared unit, preventing coarse verified values.

## Example feed

```json
[
  {"id":"coinbase","url":"https://api.coinbase.com/v2/prices/BTC-USD/spot","path":"data.amount"},
  {"id":"kraken","url":"https://api.kraken.com/0/public/Ticker?pair=XBTUSD","path":"result.XXBTZUSD.c.0"}
]
```

With `decimals=2`, a stored value of `6325400` means `63,254.00 USD`; a tick of
`100` means all validators must agree on the same whole-dollar canonical result.

## Verification

```powershell
genvm-lint check contracts\QuorumFeedCanonicalRegistry.py
python -m pytest tests\direct -v
python -m pytest tests\unit -v
npm install
npm run typecheck
```

See [CANONICAL_INVARIANT.md](CANONICAL_INVARIANT.md) for the exact stored-value,
source-status, and validator equivalence rules. Deployment addresses and live
transaction evidence are kept in `DEPLOYMENT_EVIDENCE.md` after deployment.

## License

MIT
