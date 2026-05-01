import { Transaction, TransactionInstruction } from "@solana/web3.js";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const buildAcceptPaymentInstructionsMock = vi.fn();
const validateInvoicePaymentMock = vi.fn();
const getLatestBlockhashMock = vi.fn();
const getSignaturesForAddressMock = vi.fn();
const getTransactionMock = vi.fn();
const getInvoiceIdPDAMock = vi.fn();
const connectionConstructorMock = vi.fn();
const pumpAgentConstructorMock = vi.fn();
const transactionSerializeSpy = vi.spyOn(Transaction.prototype, "serialize");
const transactionSignSpy = vi.spyOn(Transaction.prototype, "sign");
const transactionPartialSignSpy = vi.spyOn(Transaction.prototype, "partialSign");
const programIdForTests = "11111111111111111111111111111111";

vi.mock("../src/sdk-loader", () => ({
  loadPumpfunSdk: () => ({
    PumpAgent: vi.fn().mockImplementation((mint, environment, connection) => {
      pumpAgentConstructorMock(mint, environment, connection);
      return {
        buildAcceptPaymentInstructions: buildAcceptPaymentInstructionsMock,
        validateInvoicePayment: validateInvoicePaymentMock
      };
    }),
    getInvoiceIdPDA: getInvoiceIdPDAMock,
    PROGRAM_ID: { toBase58: () => programIdForTests }
  })
}));

vi.mock("@solana/web3.js", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@solana/web3.js")>();

  class MockConnection {
    readonly rpcUrl: string;

    constructor(rpcUrl: string) {
      this.rpcUrl = rpcUrl;
      connectionConstructorMock(rpcUrl);
    }

    getLatestBlockhash(commitment?: string) {
      return getLatestBlockhashMock(commitment);
    }

    getSignaturesForAddress(address: unknown, options?: unknown, commitment?: string) {
      return getSignaturesForAddressMock(address, options, commitment);
    }

    getTransaction(signature: string, options?: unknown) {
      return getTransactionMock(signature, options);
    }
  }

  return {
    ...actual,
    Connection: MockConnection
  };
});

const invoiceIdForTests = "11111111111111111111111111111111";

const buildInput = {
  userWallet: "11111111111111111111111111111111",
  agentTokenMint: "9jwExoB9h42bNeUyCH8qBJAye3NJGrToiX62DQTEpump",
  currencyMint: "So11111111111111111111111111111111111111112",
  amount: 100000000,
  memo: 123456789,
  startTime: 1_700_000_000,
  endTime: 1_700_086_400
};

const validInput = {
  ...buildInput,
  txSignature: "5".repeat(88)
};

const rpcUrl = "https://quicknode.example.invalid/secret-token";

const agentAcceptPaymentEventDiscriminator = Buffer.from([
  114, 190, 188, 192, 105, 79, 41, 147
]);

function pubkeyBytes(value: string): Buffer {
  return Buffer.from(new (require("@solana/web3.js").PublicKey)(value).toBytes());
}

function u64LE(value: number): Buffer {
  const buffer = Buffer.alloc(8);
  buffer.writeBigUInt64LE(BigInt(value));
  return buffer;
}

function i64LE(value: number): Buffer {
  const buffer = Buffer.alloc(8);
  buffer.writeBigInt64LE(BigInt(value));
  return buffer;
}

function agentAcceptPaymentEventLog(overrides: Partial<typeof validInput> = {}): string[] {
  const params = { ...validInput, ...overrides };
  const event = Buffer.concat([
    agentAcceptPaymentEventDiscriminator,
    pubkeyBytes(params.userWallet),
    pubkeyBytes(params.agentTokenMint),
    pubkeyBytes("11111111111111111111111111111111"),
    pubkeyBytes(params.currencyMint),
    u64LE(params.amount),
    u64LE(params.memo),
    i64LE(params.startTime),
    i64LE(params.endTime),
    pubkeyBytes(invoiceIdForTests),
    u64LE(0),
    i64LE(params.endTime)
  ]);
  return [`Program ${programIdForTests} invoke [1]`, `Program data: ${event.toString("base64")}`, `Program ${programIdForTests} success`];
}

describe("Pump.fun helper contract", () => {
  beforeEach(() => {
    process.env.SOLANA_RPC_URL = rpcUrl;
    buildAcceptPaymentInstructionsMock.mockResolvedValue([
      new TransactionInstruction({ keys: [], programId: new (require("@solana/web3.js").PublicKey)("11111111111111111111111111111111") })
    ]);
    validateInvoicePaymentMock.mockResolvedValue(true);
    getSignaturesForAddressMock.mockResolvedValue([{ signature: validInput.txSignature }]);
    getTransactionMock.mockResolvedValue({ meta: { err: null, logMessages: agentAcceptPaymentEventLog() } });
    getLatestBlockhashMock.mockResolvedValue({
      blockhash: "11111111111111111111111111111111",
      lastValidBlockHeight: 1
    });
    getInvoiceIdPDAMock.mockReturnValue([
      { toBase58: () => invoiceIdForTests },
      255
    ]);
  });

  afterEach(() => {
    delete process.env.SOLANA_RPC_URL;
    vi.clearAllMocks();
  });

  it("builds an unsigned payment transaction from SOLANA_RPC_URL env only", async () => {
    const { buildPaymentTransaction } = await import("../src/pumpfun-helper");

    const result = await buildPaymentTransaction(buildInput);

    expect(result.ok).toBe(true);
    if (!result.ok) throw new Error("expected build to succeed");
    expect(result.txBase64).toEqual(expect.any(String));
    expect(result.invoiceId).toBe(invoiceIdForTests);
    expect(result).not.toHaveProperty("rpcUrl");
    expect(JSON.stringify(result)).not.toContain(rpcUrl);
    expect(connectionConstructorMock).toHaveBeenCalledWith(rpcUrl);
    expect(pumpAgentConstructorMock).toHaveBeenCalledWith(
      expect.objectContaining({ toBase58: expect.any(Function) }),
      "mainnet",
      expect.anything()
    );
    expect(buildAcceptPaymentInstructionsMock).toHaveBeenCalledWith({
      user: expect.objectContaining({ toBase58: expect.any(Function) }),
      currencyMint: expect.objectContaining({ toBase58: expect.any(Function) }),
      amount: validInput.amount,
      memo: validInput.memo,
      startTime: validInput.startTime,
      endTime: validInput.endTime
    });
    expect(getLatestBlockhashMock).toHaveBeenCalledWith("confirmed");
    expect(transactionSerializeSpy).toHaveBeenCalledWith({ requireAllSignatures: false });
    expect(transactionSignSpy).not.toHaveBeenCalled();
    expect(transactionPartialSignSpy).not.toHaveBeenCalled();
  });

  it("rejects missing SOLANA_RPC_URL with a safe error code and no raw env leak", async () => {
    delete process.env.SOLANA_RPC_URL;
    const { buildPaymentTransaction } = await import("../src/pumpfun-helper");

    const result = await buildPaymentTransaction(buildInput);

    expect(result).toEqual({ ok: false, errorCode: "MISSING_SOLANA_RPC_URL" });
    expect(JSON.stringify(result)).not.toContain("SOLANA_RPC_URL=");
  });

  it("rejects rpcUrl input instead of accepting request-supplied RPC", async () => {
    const { buildPaymentTransaction } = await import("../src/pumpfun-helper");

    const result = await buildPaymentTransaction({
      ...validInput,
      rpcUrl: "https://attacker.example.invalid"
    });

    expect(result).toEqual({ ok: false, errorCode: "FORBIDDEN_FIELD" });
    expect(connectionConstructorMock).not.toHaveBeenCalled();
  });

  it("returns safe error codes instead of raw SDK/RPC errors", async () => {
    buildAcceptPaymentInstructionsMock.mockRejectedValue(
      new Error(`raw failure from ${rpcUrl}`)
    );
    const { buildPaymentTransaction } = await import("../src/pumpfun-helper");

    const result = await buildPaymentTransaction(buildInput);

    expect(result).toEqual({ ok: false, errorCode: "BUILD_PAYMENT_TRANSACTION_FAILED" });
    expect(JSON.stringify(result)).not.toContain(rpcUrl);
  });

  it("validates invoice payment with exact submitted transaction signature", async () => {
    const { validatePaymentInvoice } = await import("../src/pumpfun-helper");

    const result = await validatePaymentInvoice(validInput);

    expect(result).toEqual({ ok: true, verified: true, invoiceId: invoiceIdForTests, signatureBound: true });
    expect(validateInvoicePaymentMock).toHaveBeenCalledWith({
      user: expect.objectContaining({ toBase58: expect.any(Function) }),
      currencyMint: expect.objectContaining({ toBase58: expect.any(Function) }),
      amount: validInput.amount,
      memo: validInput.memo,
      startTime: validInput.startTime,
      endTime: validInput.endTime
    });
    expect(getSignaturesForAddressMock).toHaveBeenCalledWith(expect.objectContaining({ toBase58: expect.any(Function) }), { limit: 1000 }, "confirmed");
    expect(getTransactionMock).toHaveBeenCalledWith(validInput.txSignature, {
      commitment: "confirmed",
      maxSupportedTransactionVersion: 0
    });
    expect(JSON.stringify(result)).not.toContain(rpcUrl);
  });

  it("returns INVALID_TXSIGNATURE before any Solana lookup when submitted transaction signature is missing or malformed", async () => {
    const { validatePaymentInvoice } = await import("../src/pumpfun-helper");

    const result = await validatePaymentInvoice({
      ...buildInput,
      txSignature: "not-a-signature"
    });

    expect(result).toEqual({ ok: false, errorCode: "INVALID_TXSIGNATURE" });
    expect(getSignaturesForAddressMock).not.toHaveBeenCalled();
    expect(getTransactionMock).not.toHaveBeenCalled();
    expect(validateInvoicePaymentMock).not.toHaveBeenCalled();
  });

  it("rejects invoice validation when submitted transaction signature is not on the invoice PDA", async () => {
    getSignaturesForAddressMock.mockResolvedValue([{ signature: "6".repeat(88) }]);
    const { validatePaymentInvoice } = await import("../src/pumpfun-helper");

    const result = await validatePaymentInvoice(validInput);

    expect(result).toEqual({ ok: true, verified: false, invoiceId: invoiceIdForTests, signatureBound: false });
    expect(validateInvoicePaymentMock).not.toHaveBeenCalled();
    expect(getTransactionMock).not.toHaveBeenCalled();
  });

  it("rejects invoice validation when submitted transaction event does not match invoice terms", async () => {
    getTransactionMock.mockResolvedValue({ meta: { err: null, logMessages: agentAcceptPaymentEventLog({ amount: validInput.amount + 1 }) } });
    const { validatePaymentInvoice } = await import("../src/pumpfun-helper");

    const result = await validatePaymentInvoice(validInput);

    expect(result).toEqual({ ok: true, verified: false, invoiceId: invoiceIdForTests, signatureBound: false });
    expect(validateInvoicePaymentMock).not.toHaveBeenCalled();
  });

  it("rejects matching payment event data when it is not emitted by the Pump.fun agent-payments program", async () => {
    const otherProgram = "22222222222222222222222222222222";
    const unscopedLogs = agentAcceptPaymentEventLog().map((log) => log.replace(programIdForTests, otherProgram));
    getTransactionMock.mockResolvedValue({ meta: { err: null, logMessages: unscopedLogs } });
    const { validatePaymentInvoice } = await import("../src/pumpfun-helper");

    const result = await validatePaymentInvoice(validInput);

    expect(result).toEqual({ ok: true, verified: false, invoiceId: invoiceIdForTests, signatureBound: false });
    expect(validateInvoicePaymentMock).not.toHaveBeenCalled();
  });

  it("rejects invoice validation when submitted transaction failed", async () => {
    getTransactionMock.mockResolvedValue({ meta: { err: { InstructionError: [0, "Custom"] } } });
    const { validatePaymentInvoice } = await import("../src/pumpfun-helper");

    const result = await validatePaymentInvoice(validInput);

    expect(result).toEqual({ ok: true, verified: false, invoiceId: invoiceIdForTests, signatureBound: false });
    expect(validateInvoicePaymentMock).not.toHaveBeenCalled();
  });

  it("returns a safe validation error code only when SDK validation fails", async () => {
    validateInvoicePaymentMock.mockRejectedValue(new Error(`raw api body ${rpcUrl}`));
    const { validatePaymentInvoice } = await import("../src/pumpfun-helper");

    const result = await validatePaymentInvoice(validInput);

    expect(result).toEqual({ ok: false, errorCode: "VALIDATE_INVOICE_PAYMENT_FAILED" });
    expect(JSON.stringify(result)).not.toContain(rpcUrl);
  });
});
