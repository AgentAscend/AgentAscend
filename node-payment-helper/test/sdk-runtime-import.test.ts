import { describe, expect, it, vi } from "vitest";

vi.unmock("@pump-fun/agent-payments-sdk");
vi.unmock("@solana/web3.js");

describe("Pump.fun SDK runtime import compatibility", () => {
  it("loads the helper with the real Pump.fun SDK and returns a safe missing-env error", async () => {
    delete process.env.SOLANA_RPC_URL;

    const helper = await import("../src/pumpfun-helper");

    expect(typeof helper.buildPaymentTransaction).toBe("function");
    const result = await helper.buildPaymentTransaction({});
    expect(result).toEqual({ ok: false, errorCode: "INVALID_USERWALLET" });
  });
});
