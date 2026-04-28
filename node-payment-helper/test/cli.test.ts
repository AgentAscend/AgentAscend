import { describe, expect, it, vi } from "vitest";

const buildPaymentTransactionMock = vi.fn();
const validateInvoicePaymentMock = vi.fn();

vi.mock("../src/pumpfun-helper.js", () => ({
  buildPaymentTransaction: buildPaymentTransactionMock,
  validateInvoicePayment: validateInvoicePaymentMock
}));

const validInvoiceInput = {
  userWallet: "11111111111111111111111111111111",
  agentTokenMint: "9jwExoB9h42bNeUyCH8qBJAye3NJGrToiX62DQTEpump",
  currencyMint: "So11111111111111111111111111111111111111112",
  amount: 100000000,
  memo: 123456789,
  startTime: 1_700_000_000,
  endTime: 1_700_086_400
};

describe("CLI sanitized JSON contract", () => {
  it("routes buildPaymentTransaction JSON stdin to the helper and writes sanitized stdout", async () => {
    buildPaymentTransactionMock.mockResolvedValue({
      ok: true,
      txBase64: "base64-unsigned-transaction",
      invoiceId: "invoice-id-safe-base58"
    });
    const stdout: string[] = [];
    const stderr: string[] = [];
    const { runCli } = await import("../src/cli.js");

    const exitCode = await runCli(
      JSON.stringify({ command: "buildPaymentTransaction", input: validInvoiceInput }),
      (chunk) => stdout.push(chunk),
      (chunk) => stderr.push(chunk)
    );

    expect(exitCode).toBe(0);
    expect(buildPaymentTransactionMock).toHaveBeenCalledWith(validInvoiceInput);
    expect(JSON.parse(stdout.join(""))).toEqual({
      ok: true,
      txBase64: "base64-unsigned-transaction",
      invoiceId: "invoice-id-safe-base58"
    });
    expect(stderr.join("")).toBe("");
  });

  it("routes validateInvoicePayment JSON stdin to the helper and writes sanitized stdout", async () => {
    validateInvoicePaymentMock.mockResolvedValue({
      ok: true,
      verified: true,
      invoiceId: "invoice-id-safe-base58"
    });
    const stdout: string[] = [];
    const stderr: string[] = [];
    const { runCli } = await import("../src/cli.js");

    const exitCode = await runCli(
      JSON.stringify({ command: "validateInvoicePayment", input: validInvoiceInput }),
      (chunk) => stdout.push(chunk),
      (chunk) => stderr.push(chunk)
    );

    expect(exitCode).toBe(0);
    expect(validateInvoicePaymentMock).toHaveBeenCalledWith(validInvoiceInput);
    expect(JSON.parse(stdout.join(""))).toEqual({
      ok: true,
      verified: true,
      invoiceId: "invoice-id-safe-base58"
    });
    expect(stderr.join("")).toBe("");
  });

  it("returns nonzero and safe error JSON for invalid JSON without stderr leakage", async () => {
    const stdout: string[] = [];
    const stderr: string[] = [];
    const { runCli } = await import("../src/cli.js");

    const exitCode = await runCli("{not-json", (chunk) => stdout.push(chunk), (chunk) => stderr.push(chunk));

    expect(exitCode).toBe(2);
    expect(JSON.parse(stdout.join(""))).toEqual({ ok: false, errorCode: "INVALID_JSON" });
    expect(stderr.join("")).toBe("");
  });

  it("returns nonzero and safe error JSON for unknown command", async () => {
    const stdout: string[] = [];
    const stderr: string[] = [];
    const { runCli } = await import("../src/cli.js");

    const exitCode = await runCli(
      JSON.stringify({ command: "unknown", input: validInvoiceInput }),
      (chunk) => stdout.push(chunk),
      (chunk) => stderr.push(chunk)
    );

    expect(exitCode).toBe(2);
    expect(JSON.parse(stdout.join(""))).toEqual({ ok: false, errorCode: "UNKNOWN_COMMAND" });
    expect(stderr.join("")).toBe("");
  });

  it("preserves helper safe error codes without leaking RPC URLs or raw errors", async () => {
    validateInvoicePaymentMock.mockResolvedValue({
      ok: false,
      errorCode: "VALIDATE_INVOICE_PAYMENT_FAILED"
    });
    const stdout: string[] = [];
    const stderr: string[] = [];
    const { runCli } = await import("../src/cli.js");

    const exitCode = await runCli(
      JSON.stringify({
        command: "validateInvoicePayment",
        input: { ...validInvoiceInput, marker: "https://quicknode.example.invalid/secret-token" }
      }),
      (chunk) => stdout.push(chunk),
      (chunk) => stderr.push(chunk)
    );

    expect(exitCode).toBe(1);
    expect(JSON.parse(stdout.join(""))).toEqual({
      ok: false,
      errorCode: "VALIDATE_INVOICE_PAYMENT_FAILED"
    });
    expect(stdout.join("")).not.toContain("quicknode");
    expect(stderr.join("")).toBe("");
  });
});
