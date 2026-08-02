import { createAccount, createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { TransactionStatus } from "genlayer-js/types";

const contractAddress = process.env.CONTRACT_ADDRESS;
if (!contractAddress) throw new Error("Set CONTRACT_ADDRESS.");
const account = createAccount();
const client = createClient({ chain: studionet, account });
const sources = JSON.stringify([
  { id: "coinbase", url: "https://api.coinbase.com/v2/prices/BTC-USD/spot", path: "data.amount" },
  { id: "kraken", url: "https://api.kraken.com/0/public/Ticker?pair=XBTUSD", path: "result.XXBTZUSD.c.0" }
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
  "btc.usd.reference", "Bitcoin USD cross-exchange reference", "USD", 2,
  2, 1000, 300, sources
]);
const observationId = `btc.usd.${Date.now()}`;
const observationHash = await write("observe", ["btc.usd.reference", observationId]);
console.log(JSON.stringify({ observationId, observationHash }, null, 2));
