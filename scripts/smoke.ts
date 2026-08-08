import { createAccount, createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { TransactionStatus } from "genlayer-js/types";

const contractAddress = process.env.CONTRACT_ADDRESS;
if (!contractAddress) throw new Error("Set CONTRACT_ADDRESS.");
const sourceCommit = process.env.SOURCE_COMMIT;
if (!sourceCommit) throw new Error("Set SOURCE_COMMIT to a public Git commit SHA.");
const account = createAccount();
const client = createClient({ chain: studionet, account });
const sourceBase = `https://raw.githubusercontent.com/Starling-spell/quorumfeed-registry/${sourceCommit}/fixtures/canonical`;
const sources = JSON.stringify([
  { id: "alpha", url: `${sourceBase}/alpha.json`, path: "data.price" },
  { id: "beta", url: `${sourceBase}/beta.json`, path: "price" },
  { id: "gamma", url: `${sourceBase}/gamma.json`, path: "result.0.last" }
]);

async function write(methodName: string, args: any[]) {
  const hash = await client.writeContract({
    address: contractAddress as `0x${string}`,
    functionName: methodName,
    args,
    account,
    value: 0n
  });
  console.log(`${methodName}Hash=${hash}`);
  const receipt = await client.waitForTransactionReceipt({
    hash: hash as never,
    status: TransactionStatus.FINALIZED,
    interval: 5000,
    retries: 180
  });
  const safe = receipt as any;
  const votes = Object.values(safe.consensus_data?.votes ?? {});
  const executions = (safe.consensus_data?.leader_receipt ?? []).map(
    (item: any) => item.execution_result
  );
  console.log(`${methodName}Result=${JSON.stringify({
    status: safe.status_name,
    consensus: safe.result_name,
    agree: votes.filter((vote) => vote === "agree").length,
    disagree: votes.filter((vote) => vote === "disagree").length,
    executions
  })}`);
  return hash;
}

await write("create_feed", [
  "btc.usd.canonical", "BTC/USD canonical reproducibility feed", "USD", 2,
  2, 300, 100, sources
]);
const observationId = `btc.usd.${Date.now()}`;
const observationHash = await write("observe", ["btc.usd.canonical", observationId]);
console.log(JSON.stringify({ observationId, observationHash }, null, 2));
