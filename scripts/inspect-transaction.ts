import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { TransactionStatus } from "genlayer-js/types";

const hash = process.argv[2];
if (!hash) throw new Error("Usage: npm run inspect:transaction -- 0x...");
const client = createClient({ chain: studionet });
const receipt = await client.waitForTransactionReceipt({
  hash: hash as never,
  status: TransactionStatus.FINALIZED,
  interval: 5000,
  retries: 60
});
const safe = receipt as any;
const votes = Object.values(safe.consensus_data?.votes ?? {});
const executions = (safe.consensus_data?.leader_receipt ?? []).map(
  (item: any) => item.execution_result
);
console.log(JSON.stringify({
  hash: safe.hash,
  status: safe.status_name,
  consensus: safe.result_name,
  agree: votes.filter((vote) => vote === "agree").length,
  disagree: votes.filter((vote) => vote === "disagree").length,
  executions
}, null, 2));
