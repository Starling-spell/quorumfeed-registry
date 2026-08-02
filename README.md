# QuorumFeed Registry

QuorumFeed is a reusable GenLayer primitive for turning several public numeric
JSON feeds into one consensus-verified fixed-point observation. It is designed
for autonomous agents and contracts that need exchange rates, commodity values,
weather measurements, benchmark metrics, or other web-native numeric facts
without trusting one API or one validator.

## What is new about the approach

The contract implements a **quorum of quorums**. It first derives a median from
multiple independent sources and removes configured outliers. GenLayer
validators then independently re-fetch all sources and verify each leader datum
and the aggregate within explicit basis-point tolerances. There is no LLM and no
"well-formed output" shortcut.

## Consumer interface

- `create_feed(...)`: register an immutable declarative feed specification.
- `observe(feed_id, observation_id)`: create a validator-verified observation.
- `get_latest(feed_id)`: read the latest verified record.
- `get_observation(observation_id)`: read an immutable historical record.
- `is_verified(observation_id)`: minimal composable consumer gate.
- `deactivate_feed(feed_id)`: creator safety switch; history remains available.

Each source specifies an HTTPS URL and a dotted JSON path. Array indexes are
supported as numeric path segments. Values are converted to fixed-point integers
at the feed's declared decimal precision.

## Example feed

```json
[
  {"id":"coinbase","url":"https://api.coinbase.com/v2/prices/BTC-USD/spot","path":"data.amount"},
  {"id":"kraken","url":"https://api.kraken.com/0/public/Ticker?pair=XBTUSD","path":"result.XXBTZUSD.c.0"}
]
```

With `decimals=2`, a stored value of `6321450` means `63,214.50 USD`.

## Verification

```powershell
genvm-lint check contracts\QuorumFeedRegistry.py
python -m pytest tests\direct -v
python -m pytest tests\unit -v
npm install
npm run typecheck
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the trust boundary and exact
equivalence rule. Deployment addresses and live transaction evidence are kept in
`DEPLOYMENT_EVIDENCE.md` after deployment.

## License

MIT
