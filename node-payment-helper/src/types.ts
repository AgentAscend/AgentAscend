export type SafeErrorCode =
  | "INVALID_USERWALLET"
  | "INVALID_AGENTTOKENMINT"
  | "INVALID_CURRENCYMINT"
  | "INVALID_AMOUNT"
  | "INVALID_MEMO"
  | "INVALID_STARTTIME"
  | "INVALID_ENDTIME"
  | "INVALID_TIME_RANGE"
  | "FORBIDDEN_FIELD"
  | "MISSING_SOLANA_RPC_URL"
  | "BUILD_PAYMENT_TRANSACTION_FAILED"
  | "VALIDATE_INVOICE_PAYMENT_FAILED";

export interface InvoiceParamsInput {
  userWallet: string;
  agentTokenMint: string;
  currencyMint: string;
  amount: number;
  memo: number;
  startTime: number;
  endTime: number;
}

export type ValidationResult<T> =
  | { ok: true; value: T }
  | { ok: false; errorCode: SafeErrorCode };

export type BuildPaymentTransactionResult =
  | { ok: true; txBase64: string; invoiceId?: string }
  | { ok: false; errorCode: SafeErrorCode };

export type ValidateInvoicePaymentResult =
  | { ok: true; verified: boolean; invoiceId?: string }
  | { ok: false; errorCode: SafeErrorCode };
