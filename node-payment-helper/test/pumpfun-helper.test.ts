import { Transaction, TransactionInstruction } from "@solana/web3.js";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const buildAcceptPaymentInstructionsMock = vi.fn();
const validateInvoicePaymentMock = vi.fn();
const getLatestBlockhashMock = vi.fn();
const getInvoiceIdPDAMock = vi.fn();
const connectionConstructorMock = vi.fn();
const pumpAgentConstructorMock = vi.fn();
const transactionSerializeSpy = vi.spyOn(Transaction.prototype, "serialize");
const transactionSignSpy = vi.spyOn(Transaction.prototype, "sign");
const transactionPartialSignSpy = vi.spyOn(Transaction.prototype, "partialSign");

vi.mock("../src/sdk-loader", () => ({
  loadPumpfunSdk: () => ({
    PumpAgent: vi.fn().mockImplementation((mint, environment, connection) => {
      pumpAgentConstructorMock(mint, environment, connection);
      return {
        buildAcceptPaymentInstructions: buildAcceptPaymentInstructionsMock,
        validateInvoicePayment: validateInvoicePaymentMock
      };
    }),
    getInvoiceIdPDA: getInvoiceIdPDAMock
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
  }

  return {
    ...actual,
    Connection: MockConnection
  };
});

const validInput = {
  userWallet: "11111111111111111111111111111111",
  agentTokenMint: "9jwExoB9h42bNeUyCH8qBJAye3NJGrToiX62DQTEpump",
  currencyMint: "So11111111111111111111111111111111111111112",
  amount: 100000000,
  memo: 123456789,
  startTime: 1_700_000_000,
  endTime: 1_700_086_400
};

const rpcUrl = "https://quicknode.example.invalid/secret-token";

describe("Pump.fun helper contract", () => {
  beforeEach(() => {
    process.env.SOLANA_RPC_URL = rpcUrl;
    buildAcceptPaymentInstructionsMock.mockResolvedValue([
      new TransactionInstruction({ keys: [], programId: new (require("@solana/web3.js").PublicKey)("11111111111111111111111111111111") })
    ]);
    validateInvoicePaymentMock.mockResolvedValue(true);
    getLatestBlockhashMock.mockResolvedValue({
      blockhash: "11111111111111111111111111111111",
      lastValidBlockHeight: 1
    });
    getInvoiceIdPDAMock.mockReturnValue([
      { toBase58: () => "invoice-id-safe-base58" },
      255
    ]);
  });

  afterEach(() => {
    delete process.env.SOLANA_RPC_URL;
    vi.clearAllMocks();
  });

  it("builds an unsigned payment transaction from SOLANA_RPC_URL env only", async () => {
    const { buildPaymentTransaction } = await import("../src/pumpfun-helper");

    const result = await buildPaymentTransaction(validInput);

    expect(result.ok).toBe(true);
    if (!result.ok) throw new Error("expected build to succeed");
    expect(result.txBase64).toEqual(expect.any(String));
    expect(result.invoiceId).toBe("invoice-id-safe-base58");
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

    const result = await buildPaymentTransaction(validInput);

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

    const result = await buildPaymentTransaction(validInput);

    expect(result).toEqual({ ok: false, errorCode: "BUILD_PAYMENT_TRANSACTION_FAILED" });
    expect(JSON.stringify(result)).not.toContain(rpcUrl);
  });

  it("validates invoice payment with exact numeric params and does not write DB or grant access", async () => {
    const { validatePaymentInvoice } = await import("../src/pumpfun-helper");

    const result = await validatePaymentInvoice(validInput);

    expect(result).toEqual({ ok: true, verified: true, invoiceId: "invoice-id-safe-base58" });
    expect(validateInvoicePaymentMock).toHaveBeenCalledWith({
      user: expect.objectContaining({ toBase58: expect.any(Function) }),
      currencyMint: expect.objectContaining({ toBase58: expect.any(Function) }),
      amount: validInput.amount,
      memo: validInput.memo,
      startTime: validInput.startTime,
      endTime: validInput.endTime
    });
    expect(JSON.stringify(result)).not.toContain(rpcUrl);
  });

  it("returns a safe validation error code only when SDK validation fails", async () => {
    validateInvoicePaymentMock.mockRejectedValue(new Error(`raw api body ${rpcUrl}`));
    const { validatePaymentInvoice } = await import("../src/pumpfun-helper");

    const result = await validatePaymentInvoice(validInput);

    expect(result).toEqual({ ok: false, errorCode: "VALIDATE_INVOICE_PAYMENT_FAILED" });
    expect(JSON.stringify(result)).not.toContain(rpcUrl);
  });
});
