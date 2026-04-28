import { createRequire } from "node:module";
import type { PublicKey, TransactionInstruction } from "@solana/web3.js";

type InvoiceId = { toBase58(): string };

type PumpfunSdk = {
  PumpAgent: new (agentMint: PublicKey, environment: "mainnet" | "devnet", connection: unknown) => {
    buildAcceptPaymentInstructions(args: Record<string, unknown>): Promise<TransactionInstruction[]>;
    validateInvoicePayment(args: Record<string, unknown>): Promise<boolean>;
  };
  getInvoiceIdPDA: (...args: unknown[]) => [InvoiceId, number];
};

const require = createRequire(import.meta.url);
let cachedSdk: PumpfunSdk | undefined;

export function loadPumpfunSdk(): PumpfunSdk {
  if (!cachedSdk) {
    cachedSdk = require("@pump-fun/agent-payments-sdk") as PumpfunSdk;
  }
  return cachedSdk;
}
