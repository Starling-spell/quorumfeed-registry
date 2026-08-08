# StudioNet deployment evidence

## Corrected v2: canonical exact-equivalence deployment

This is the deployment for the corrected submission. The preceding v1 section
is retained solely as historical evidence and must not be used for resubmission.

- Address: `0x6Fd6ACA146cBAa99088C92D8AAEe01f6b20A6cb6`
- Explorer: https://explorer-studio.genlayer.com/address/0x6Fd6ACA146cBAa99088C92D8AAEe01f6b20A6cb6
- Deployment transaction: https://explorer-studio.genlayer.com/tx/0x3bcb70c516c94a78109d7650227c70ce412888a1a8c642501f18543e5356300a
- Deployment consensus: `FINALIZED`, `MAJORITY_AGREE` (3 agree, 0 disagree); all executions `SUCCESS`
- Normalized deployed/local SHA-256: `275ad258e37f281c698dbc4d3cea0d22993f29570a2a56691393c78f9e978bbe`

### Live corrected consensus proof

- Commit-pinned fixture revision: `0d1c42f3af31acde05702c1a7ed1663e44655e55`
- Feed creation: https://explorer-studio.genlayer.com/tx/0x5dd92e924790e62d4001433489aa938af067efb080dcf3290ab96371e3debefa
- Observation: https://explorer-studio.genlayer.com/tx/0x5f1a47adc087482f86890381eeeac887bb07772ab43c4db0f09ffb9a0347f083
- Observation ID: `btc.usd.1786220859507`
- Consensus: `FINALIZED`, `MAJORITY_AGREE` (3 agree, 0 disagree); all executions `SUCCESS`
- Stored record: `value=6325500`, `canonical_value=6325500`, `canonical_tick=100`, `decimals=2` (`63,255.00 USD`)
- Bound recomputation fields: `source_count=3`, `inlier_count=2`, `outlier_count=1`; `alpha=inlier`, `beta=inlier`, `gamma=outlier`; `verified=true`

The leader's proof is recomputed into this exact public record before it can be
accepted. Validators independently re-fetch every source and accept only if
their separately recomputed public record is byte-for-byte equal, so tolerance
cannot admit an alternative stored oracle value or different source statuses.

## Historical v1 deployment (superseded)

## Contract

- Address: `0x744eC062010c4Bf912A482D4ba9E344B2f055e23`
- Explorer: https://explorer-studio.genlayer.com/address/0x744eC062010c4Bf912A482D4ba9E344B2f055e23
- Deployment transaction: https://explorer-studio.genlayer.com/tx/0xca0a162739c3256d41003ea0925b4a6d1e54ddf9734dfefa26b1048f24248d91
- Deployment: `FINALIZED`, execution `SUCCESS`
- Normalized deployed/local SHA-256: `66343bada4a68b2e22a135af3a7207326c47e706c726d6da5a7f440d67d77644`

## Live consensus proof

- Feed creation transaction: https://explorer-studio.genlayer.com/tx/0x60db21aefa0c59fe7210079ce67a4cbda4c04272888e03ef098ae4e26205c583
- Observation transaction: https://explorer-studio.genlayer.com/tx/0x1bbca0101a06aff11b5ee8be682419a97d4f5b32cce685aadc2509c05828212e
- Observation ID: `btc.usd.1785699105480`
- Consensus: `MAJORITY_AGREE` (3 agree, 0 disagree)
- Stored gate: `verified=true`
- Fixed-point result: `6325481` with 2 decimals = `63,254.81 USD`
- Coinbase source: `6325262`
- Kraken source: `6325700`

The value was not supplied by the caller. Leader and validators independently
requested both canonical exchange APIs, parsed distinct JSON paths, normalized
the values to integer cents, recomputed the median, and applied the configured
source and validator tolerances.

## Reproduce safe checks

```powershell
$env:CONTRACT_ADDRESS='0x744eC062010c4Bf912A482D4ba9E344B2f055e23'
$env:DEPLOY_TX='0xca0a162739c3256d41003ea0925b4a6d1e54ddf9734dfefa26b1048f24248d91'
npm run verify:deployment
npm run read:latest
```
