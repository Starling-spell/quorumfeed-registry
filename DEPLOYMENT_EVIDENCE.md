# StudioNet deployment evidence

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
