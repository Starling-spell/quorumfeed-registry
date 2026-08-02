import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";

const address = process.env.CONTRACT_ADDRESS as `0x${string}` | undefined;
if (!address) throw new Error("Set CONTRACT_ADDRESS.");
const client = createClient({ chain: studionet });
const record = await client.readContract({
  address,
  functionName: "get_latest",
  args: ["btc.usd.reference"]
}) as Record<string, any>;
console.log(JSON.stringify({
  contractAddress: address,
  observationId: record.observation_id,
  feedId: record.feed_id,
  value: record.value,
  decimals: record.decimals,
  unit: record.unit,
  sourceCount: record.source_count,
  sourceValues: record.source_values,
  spreadBps: record.spread_bps,
  verified: record.verified
}, null, 2));
