import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";

const address = process.env.CONTRACT_ADDRESS as `0x${string}` | undefined;
if (!address) throw new Error("Set CONTRACT_ADDRESS.");
const feedId = process.env.FEED_ID ?? "btc.usd.canonical";
const client = createClient({ chain: studionet });
const record = await client.readContract({
  address,
  functionName: "get_latest",
  args: [feedId]
}) as Record<string, any>;
console.log(JSON.stringify({
  contractAddress: address,
  observationId: record.observation_id,
  feedId: record.feed_id,
  value: record.value,
  decimals: record.decimals,
  unit: record.unit,
  canonicalValue: record.canonical_value,
  canonicalTick: record.canonical_tick,
  sourceCount: record.source_count,
  inlierCount: record.inlier_count,
  outlierCount: record.outlier_count,
  sourceStatuses: record.source_statuses,
  verificationMode: record.verification_mode,
  verified: record.verified
}, null, 2));
