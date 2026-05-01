import { Connection, PublicKey, Transaction } from "@solana/web3.js";
import { loadPumpfunSdk } from "./sdk-loader.js";
import type {
  BuildPaymentTransactionResult,
  InvoiceParamsInput,
  ValidateInvoicePaymentInput,
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

const AGENT_ACCEPT_PAYMENT_EVENT_DISCRIMINATOR = Buffer.from([
  114, 190, 188, 192, 105, 79, 41, 147
]);
const AGENT_ACCEPT_PAYMENT_EVENT_MIN_LENGTH = 8 + 32 + 32 + 32 + 32 + 8 + 8 + 8 + 8 + 32;

function readU64LE(data: Buffer, offset: number): bigint {
  return data.readBigUInt64LE(offset);
}

function readI64LE(data: Buffer, offset: number): bigint {
  return data.readBigInt64LE(offset);
}

function readPublicKey(data: Buffer, offset: number): PublicKey {
  return new PublicKey(data.subarray(offset, offset + 32));
}

function decodeProgramDataLog(log: string): Buffer | undefined {
  const prefix = "Program data: ";
  if (!log.startsWith(prefix)) {
    return undefined;
  }

  try {
    return Buffer.from(log.slice(prefix.length), "base64");
  } catch {
    return undefined;
  }
}

function logHasMatchingAgentAcceptPaymentEvent(
  log: string,
  params: ValidateInvoicePaymentInput,
  invoiceId: PublicKey
): boolean {
  const data = decodeProgramDataLog(log);
  if (!data || data.length < AGENT_ACCEPT_PAYMENT_EVENT_MIN_LENGTH) {
    return false;
  }
  if (!data.subarray(0, 8).equals(AGENT_ACCEPT_PAYMENT_EVENT_DISCRIMINATOR)) {
    return false;
  }

  let offset = 8;
  const user = readPublicKey(data, offset);
  offset += 32;
  const tokenizedAgentMint = readPublicKey(data, offset);
  offset += 32;
  offset += 32; // tokenAgentPayments
  const currencyMint = readPublicKey(data, offset);
  offset += 32;
  const amount = readU64LE(data, offset);
  offset += 8;
  const memo = readU64LE(data, offset);
  offset += 8;
  const startTime = readI64LE(data, offset);
  offset += 8;
  const endTime = readI64LE(data, offset);
  offset += 8;
  const eventInvoiceId = readPublicKey(data, offset);

  return (
    user.equals(new PublicKey(params.userWallet)) &&
    tokenizedAgentMint.equals(new PublicKey(params.agentTokenMint)) &&
    currencyMint.equals(new PublicKey(params.currencyMint)) &&
    amount === BigInt(params.amount) &&
    memo === BigInt(params.memo) &&
    startTime === BigInt(params.startTime) &&
    endTime === BigInt(params.endTime) &&
    eventInvoiceId.equals(invoiceId)
  );
}

function transactionHasExactPaymentEvent(
  logMessages: string[] | null | undefined,
  params: ValidateInvoicePaymentInput,
  invoiceId: PublicKey,
  programId: PublicKey
): boolean {
  if (!logMessages) {
    return false;
  }

  const programStack: string[] = [];
  const programIdBase58 = programId.toBase58();

  for (const log of logMessages) {
    const invokeMatch = /^Program ([1-9A-HJ-NP-Za-km-z]{32,44}) invoke \[\d+\]$/.exec(log);
    if (invokeMatch) {
      programStack.push(invokeMatch[1]);
      continue;
    }

    if (
      programStack[programStack.length - 1] === programIdBase58 &&
      logHasMatchingAgentAcceptPaymentEvent(log, params, invoiceId)
    ) {
      return true;
    }

    const exitMatch = /^Program ([1-9A-HJ-NP-Za-km-z]{32,44}) (success|failed:.*)$/.exec(log);
    if (exitMatch) {
      const lastIndex = programStack.lastIndexOf(exitMatch[1]);
      if (lastIndex >= 0) {
        programStack.splice(lastIndex, 1);
      }
    }
  }

  return false;
}

function readPumpfunProgramId(): PublicKey | undefined {
  const sdk = loadPumpfunSdk() as ReturnType<typeof loadPumpfunSdk> & {
    PROGRAM_ID?: PublicKey;
    PUMP_AGENT_PAYMENTS_PROGRAM_ID?: PublicKey;
  };
  const programId = sdk.PROGRAM_ID ?? sdk.PUMP_AGENT_PAYMENTS_PROGRAM_ID;
  return programId ? new PublicKey(programId.toBase58()) : undefined;
}

async function submittedSignatureTouchesExactInvoice(
  connection: Connection,
  params: ValidateInvoicePaymentInput
): Promise<boolean> {
  const invoiceId = deriveInvoiceId(params);
  const programId = readPumpfunProgramId();
  if (!invoiceId || !programId) {
    return false;
  }

  const invoicePublicKey = new PublicKey(invoiceId);
  const signatures = await connection.getSignaturesForAddress(invoicePublicKey, { limit: 1000 }, "confirmed");
  const submitted = signatures.find((entry) => entry.signature === params.txSignature);
  if (!submitted || submitted.err) {
    return false;
  }

  const transaction = await connection.getTransaction(params.txSignature, {
    commitment: "confirmed",
    maxSupportedTransactionVersion: 0
  });
  if (!transaction || transaction.meta?.err) {
    return false;
  }

  return transactionHasExactPaymentEvent(transaction.meta?.logMessages, params, invoicePublicKey, programId);
}

export async function buildPaymentTransaction(
  input: Record<string, unknown>
): Promise<BuildPaymentTransactionResult> {
  const validated = validateBuildPaymentTransactionInput(input);
  if (validated.ok === false) {
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
  if (validated.ok === false) {
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

    const signatureBound = await submittedSignatureTouchesExactInvoice(connection, params);
    if (!signatureBound) {
      return {
        ok: true,
        verified: false,
        invoiceId: deriveInvoiceId(params),
        signatureBound: false
      };
    }

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
      invoiceId: deriveInvoiceId(params),
      signatureBound: true
    };
  } catch {
    return { ok: false, errorCode: "VALIDATE_INVOICE_PAYMENT_FAILED" };
  }
}

export const validatePaymentInvoice = validateInvoicePayment;
