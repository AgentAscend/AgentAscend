#!/usr/bin/env node
import { buildPaymentTransaction, validateInvoicePayment } from "./pumpfun-helper.js";
import type {
  BuildPaymentTransactionResult,
  SafeErrorCode,
  ValidateInvoicePaymentResult
} from "./types.js";

type CliCommand = "buildPaymentTransaction" | "validateInvoicePayment";
type CliResult = BuildPaymentTransactionResult | ValidateInvoicePaymentResult | { ok: false; errorCode: SafeErrorCode };
type WriteFn = (chunk: string) => void;

function safeFailure(errorCode: SafeErrorCode): { ok: false; errorCode: SafeErrorCode } {
  return { ok: false, errorCode };
}

function writeJson(writeStdout: WriteFn, result: CliResult): void {
  writeStdout(`${JSON.stringify(result)}\n`);
}

function parseRequest(stdin: string):
  | { ok: true; command: CliCommand; input: Record<string, unknown> }
  | { ok: false; errorCode: SafeErrorCode } {
  let parsed: unknown;
  try {
    parsed = JSON.parse(stdin);
  } catch {
    return safeFailure("INVALID_JSON");
  }

  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    return safeFailure("INVALID_REQUEST");
  }

  const request = parsed as Record<string, unknown>;
  const { command, input } = request;

  if (command !== "buildPaymentTransaction" && command !== "validateInvoicePayment") {
    return safeFailure("UNKNOWN_COMMAND");
  }

  if (typeof input !== "object" || input === null || Array.isArray(input)) {
    return safeFailure("INVALID_REQUEST");
  }

  return { ok: true, command, input: input as Record<string, unknown> };
}

export async function runCli(
  stdin: string,
  writeStdout: WriteFn = (chunk) => process.stdout.write(chunk),
  _writeStderr: WriteFn = () => undefined
): Promise<number> {
  const request = parseRequest(stdin);
  if (!request.ok) {
    writeJson(writeStdout, request);
    return 2;
  }

  const result = request.command === "buildPaymentTransaction"
    ? await buildPaymentTransaction(request.input)
    : await validateInvoicePayment(request.input);

  writeJson(writeStdout, result);
  return result.ok ? 0 : 1;
}

async function readStdin(): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  return Buffer.concat(chunks).toString("utf8");
}

if (process.argv[1] && import.meta.url === new URL(process.argv[1], "file:").href) {
  const stdin = await readStdin();
  process.exitCode = await runCli(stdin);
}
