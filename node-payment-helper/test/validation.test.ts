import { describe, expect, it } from "vitest";
import {
  validateBuildPaymentTransactionInput,
  validateInvoicePaymentInput
} from "../src/validation";

const baseInput = {
  userWallet: "11111111111111111111111111111111",
  agentTokenMint: "9jwExoB9h42bNeUyCH8qBJAye3NJGrToiX62DQTEpump",
  currencyMint: "So11111111111111111111111111111111111111112",
  amount: 100000000,
  memo: 123456789,
  startTime: 1_700_000_000,
  endTime: 1_700_086_400
};

describe("invoice parameter validation", () => {
  it.each([
    "userWallet",
    "agentTokenMint",
    "currencyMint",
    "amount",
    "memo",
    "startTime",
    "endTime"
  ] as const)("requires %s for buildPaymentTransaction", (field) => {
    const input = { ...baseInput } as Record<string, unknown>;
    delete input[field];

    const result = validateBuildPaymentTransactionInput(input);

    expect(result.ok).toBe(false);
    expect(result.errorCode).toBe(`INVALID_${field.toUpperCase()}`);
  });

  it.each([
    "userWallet",
    "agentTokenMint",
    "currencyMint",
    "amount",
    "memo",
    "startTime",
    "endTime"
  ] as const)("requires %s for validateInvoicePayment", (field) => {
    const input = { ...baseInput } as Record<string, unknown>;
    delete input[field];

    const result = validateInvoicePaymentInput(input);

    expect(result.ok).toBe(false);
    expect(result.errorCode).toBe(`INVALID_${field.toUpperCase()}`);
  });

  it.each([0, -1, Number.NaN, Number.POSITIVE_INFINITY])(
    "rejects non-positive or invalid amount %s",
    (amount) => {
      const result = validateBuildPaymentTransactionInput({ ...baseInput, amount });

      expect(result.ok).toBe(false);
      expect(result.errorCode).toBe("INVALID_AMOUNT");
    }
  );

  it("requires endTime to be greater than startTime", () => {
    const result = validateBuildPaymentTransactionInput({
      ...baseInput,
      startTime: 1_700_000_000,
      endTime: 1_700_000_000
    });

    expect(result.ok).toBe(false);
    expect(result.errorCode).toBe("INVALID_TIME_RANGE");
  });

  it.each([0, -1, 1.5, Number.NaN, Number.POSITIVE_INFINITY])(
    "rejects invalid Unix timestamp %s",
    (timestamp) => {
      const result = validateBuildPaymentTransactionInput({
        ...baseInput,
        startTime: timestamp
      });

      expect(result.ok).toBe(false);
      expect(result.errorCode).toBe("INVALID_STARTTIME");
    }
  );

  it("rejects rpcUrl in helper input", () => {
    const result = validateBuildPaymentTransactionInput({
      ...baseInput,
      rpcUrl: "https://example.invalid"
    });

    expect(result.ok).toBe(false);
    expect(result.errorCode).toBe("FORBIDDEN_FIELD");
  });

  it.each(["privateKey", "secretKey"])("rejects %s in helper input", (field) => {
    const result = validateBuildPaymentTransactionInput({
      ...baseInput,
      [field]: "do-not-accept"
    });

    expect(result.ok).toBe(false);
    expect(result.errorCode).toBe("FORBIDDEN_FIELD");
  });

  it("requires validateInvoicePayment numeric params to be numbers", () => {
    const result = validateInvoicePaymentInput({
      ...baseInput,
      amount: "100000000",
      memo: "123456789",
      startTime: "1700000000",
      endTime: "1700086400"
    });

    expect(result.ok).toBe(false);
    expect(result.errorCode).toBe("INVALID_AMOUNT");
  });

  it("accepts valid invoice parameters", () => {
    const result = validateBuildPaymentTransactionInput(baseInput);

    expect(result).toEqual({ ok: true, value: baseInput });
  });
});
