import { Connection, PublicKey, Transaction } from "@solana/web3.js";
import { loadPumpfunSdk } from "./sdk-loader.js";
import type {
  BuildPaymentTransactionResult,
  InvoiceParamsInput,
  ValidateInvoicePaymentResult
} from "./types.js";
import {
  validateBuildPaymentTransactionInput,
  validateInvoicePaymentInput
} from "./validation.js";

function readSolanaRpcUrl(): string | undefined {
  const rpcUrl = process.env.SOLANA_RPC_URL;
  return typeof rpcUrl === "string" && rpcUrl.trim().length > 0 ? rpcUrl : undefined;
}

function deriveInvoiceId(params: Pick<InvoiceParamsInput, "agentTokenMint" | "currencyMint" | "amount" | "memo" | "startTime" | "endTime">): string | undefined {
  try {
    const { getInvoiceIdPDA } = loadPumpfunSdk();
    const [invoiceId] = getInvoiceIdPDA(
      new PublicKey(params.agentTokenMint),
      new PublicKey(params.currencyMint),
      params.amount,
      params.memo,
      params.startTime,
      params.endTime
    );

    return invoiceId.toBase58();
  } catch {
    return undefined;
  }
}

export async function buildPaymentTransaction(
  input: Record<string, unknown>
): Promise<BuildPaymentTransactionResult> {
  const validated = validateBuildPaymentTransactionInput(input);
  if (!validated.ok) {
    return { ok: false, errorCode: validated.errorCode };
  }

  const rpcUrl = readSolanaRpcUrl();
  if (!rpcUrl) {
    return { ok: false, errorCode: "MISSING_SOLANA_RPC_URL" };
  }

  const params = validated.value;

  try {
    const { PumpAgent } = loadPumpfunSdk();
    const connection = new Connection(rpcUrl);
    const agentMint = new PublicKey(params.agentTokenMint);
    const currencyMint = new PublicKey(params.currencyMint);
    const user = new PublicKey(params.userWallet);
    const agent = new PumpAgent(agentMint, "mainnet", connection);

    const instructions = await agent.buildAcceptPaymentInstructions({
      user,
      currencyMint,
      amount: params.amount,
      memo: params.memo,
      startTime: params.startTime,
      endTime: params.endTime
    });

    const { blockhash } = await connection.getLatestBlockhash("confirmed");
    const tx = new Transaction();
    tx.recentBlockhash = blockhash;
    tx.feePayer = user;
    tx.add(...instructions);

    const txBase64 = tx
      .serialize({ requireAllSignatures: false })
      .toString("base64");

    return {
      ok: true,
      txBase64,
      invoiceId: deriveInvoiceId(params)
    };
  } catch {
    return { ok: false, errorCode: "BUILD_PAYMENT_TRANSACTION_FAILED" };
  }
}

export async function validateInvoicePayment(
  input: Record<string, unknown>
): Promise<ValidateInvoicePaymentResult> {
  const validated = validateInvoicePaymentInput(input);
  if (!validated.ok) {
    return { ok: false, errorCode: validated.errorCode };
  }

  const rpcUrl = readSolanaRpcUrl();
  if (!rpcUrl) {
    return { ok: false, errorCode: "MISSING_SOLANA_RPC_URL" };
  }

  const params = validated.value;

  try {
    const { PumpAgent } = loadPumpfunSdk();
    const connection = new Connection(rpcUrl);
    const agentMint = new PublicKey(params.agentTokenMint);
    const currencyMint = new PublicKey(params.currencyMint);
    const user = new PublicKey(params.userWallet);
    const agent = new PumpAgent(agentMint, "mainnet", connection);

    const verified = await agent.validateInvoicePayment({
      user,
      currencyMint,
      amount: params.amount,
      memo: params.memo,
      startTime: params.startTime,
      endTime: params.endTime
    });

    return {
      ok: true,
      verified,
      invoiceId: deriveInvoiceId(params)
    };
  } catch {
    return { ok: false, errorCode: "VALIDATE_INVOICE_PAYMENT_FAILED" };
  }
}

export const validatePaymentInvoice = validateInvoicePayment;
