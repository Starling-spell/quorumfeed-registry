import fs from "node:fs";
import path from "node:path";
import { createAccount, createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { TransactionStatus } from "genlayer-js/types";

const account = createAccount();
const client = createClient({ chain: studionet, account });
const code = fs.readFileSync(
  path.resolve(process.cwd(), "contracts/QuorumFeedCanonicalRegistry.py"),
  "utf8"
);

console.log(`Deploying QuorumFeedCanonicalRegistry as ${account.address} ...`);
const transactionHash = await client.deployContract({ account, code, args: [] });
console.log(`transactionHash=${transactionHash}`);
const receipt = (await client.waitForTransactionReceipt({
  hash: transactionHash as never,
  status: TransactionStatus.FINALIZED,
  interval: 5000,
  retries: 180
})) as Record<string, unknown>;
const data = receipt.data as { contract_address?: string } | undefined;
const decoded = receipt.txDataDecoded as { contractAddress?: string } | undefined;
const contractAddress = data?.contract_address ?? decoded?.contractAddress;
if (!contractAddress) throw new Error("No contract address in finalized deployment.");
console.log(JSON.stringify({
  contractAddress,
  transactionHash,
  explorerUrl: `https://explorer-studio.genlayer.com/address/${contractAddress}`,
  transactionUrl: `https://explorer-studio.genlayer.com/tx/${transactionHash}`
}, null, 2));
