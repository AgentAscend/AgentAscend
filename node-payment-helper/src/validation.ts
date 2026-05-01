import type { InvoiceParamsInput, ValidateInvoicePaymentInput, ValidationResult } from "./types.js";

const forbiddenInputFields = ["rpcUrl", "privateKey", "secretKey"] as const;

function hasForbiddenField(input: Record<string, unknown>): boolean {
  return forbiddenInputFields.some((field) => Object.prototype.hasOwnProperty.call(input, field));
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isPositiveInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && Number.isFinite(value) && value > 0;
}

function isValidUnixTimestamp(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && Number.isFinite(value) && value > 0;
}

function isLikelyTransactionSignature(value: unknown): value is string {
  return typeof value === "string" && /^[1-9A-HJ-NP-Za-km-z]{80,100}$/.test(value.trim());
}

export function validateBuildPaymentTransactionInput(
  input: Record<string, unknown>
): ValidationResult<InvoiceParamsInput> {
  return validateInvoiceParams(input);
}

export function validateInvoicePaymentInput(
  input: Record<string, unknown>
): ValidationResult<ValidateInvoicePaymentInput> {
  const invoiceParams = validateInvoiceParams(input);
  if (invoiceParams.ok === false) {
    return { ok: false, errorCode: invoiceParams.errorCode };
  }
  if (!isLikelyTransactionSignature(input.txSignature)) {
    return { ok: false, errorCode: "INVALID_TXSIGNATURE" };
  }
  return {
    ok: true,
    value: {
      ...invoiceParams.value,
      txSignature: input.txSignature.trim()
    }
  };
}

function validateInvoiceParams(input: Record<string, unknown>): ValidationResult<InvoiceParamsInput> {
  if (hasForbiddenField(input)) {
    return { ok: false, errorCode: "FORBIDDEN_FIELD" };
  }

  if (!isNonEmptyString(input.userWallet)) {
    return { ok: false, errorCode: "INVALID_USERWALLET" };
  }

  if (!isNonEmptyString(input.agentTokenMint)) {
    return { ok: false, errorCode: "INVALID_AGENTTOKENMINT" };
  }

  if (!isNonEmptyString(input.currencyMint)) {
    return { ok: false, errorCode: "INVALID_CURRENCYMINT" };
  }

  if (!isPositiveInteger(input.amount)) {
    return { ok: false, errorCode: "INVALID_AMOUNT" };
  }

  if (!isPositiveInteger(input.memo)) {
    return { ok: false, errorCode: "INVALID_MEMO" };
  }

  if (!isValidUnixTimestamp(input.startTime)) {
    return { ok: false, errorCode: "INVALID_STARTTIME" };
  }

  if (!isValidUnixTimestamp(input.endTime)) {
    return { ok: false, errorCode: "INVALID_ENDTIME" };
  }

  if (input.endTime <= input.startTime) {
    return { ok: false, errorCode: "INVALID_TIME_RANGE" };
  }

  return {
    ok: true,
    value: {
      userWallet: input.userWallet,
      agentTokenMint: input.agentTokenMint,
      currencyMint: input.currencyMint,
      amount: input.amount,
      memo: input.memo,
      startTime: input.startTime,
      endTime: input.endTime
    }
  };
}
