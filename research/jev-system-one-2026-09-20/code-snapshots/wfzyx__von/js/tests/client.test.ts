import { describe, expect, it } from "bun:test";
import { VonClient, TypeSafeClient, choice, noul, score } from "../src/index.js";

describe("Von JavaScript/TypeScript SDK", () => {
  it("exports TypeSafeClient drop-in alias", () => {
    expect(TypeSafeClient).toBe(VonClient);
    const client = new TypeSafeClient({ baseURL: "http://localhost:8000" });
    expect(client.baseURL).toBe("http://localhost:8000");
  });

  it("builds valid Choice questions", () => {
    const q = choice("Select department", { billing: "Invoices", tech: "Bugs" });
    expect(q.type).toBe("choice");
    expect(q.instructions).toBe("Select department");
    expect(q.criteria).toEqual({ billing: "Invoices", tech: "Bugs" });

    const qArr = choice("Select option", ["opt_a", "opt_b"]);
    expect(qArr.criteria).toEqual({ opt_a: null, opt_b: null });
  });

  it("builds valid Noul questions", () => {
    const q = noul("Is database down?", { pos: "Down", neg: "Up" });
    expect(q.type).toBe("noul");
    expect(q.criteria?.pos).toBe("Down");
    expect(q.criteria?.neg).toBe("Up");
  });

  it("builds valid Score questions", () => {
    const q = score("Rate severity", ["Low", "Medium", "High"]);
    expect(q.type).toBe("score");
    expect(q.criteria).toEqual(["Low", "Medium", "High"]);
  });

  it("constructs payload correctly in systemOne mock", async () => {
    let capturedUrl = "";
    let capturedBody: any = null;

    const mockFetch = async (url: string, init: any) => {
      capturedUrl = url;
      capturedBody = JSON.parse(init.body);
      return {
        ok: true,
        json: async () => ({
          model: "von-1.0.0",
          answers: {
            dept: {
              type: "choice",
              choice: "billing",
              confidence: 0.92,
              probabilities: { billing: 0.92, tech: 0.08 },
            },
          },
          usage: { input_tokens: 10, output_tokens: 8 },
        }),
      };
    };

    // Override global fetch for testing
    const originalFetch = globalThis.fetch;
    globalThis.fetch = mockFetch as any;

    try {
      const client = new VonClient({ baseURL: "http://127.0.0.1:9000", apiKey: "test_token" });
      const resp = await client.systemOne({
        state: "Refund requested",
        questions: { dept: choice("Department", { billing: "billing", tech: "tech" }) },
      });

      expect(capturedUrl).toBe("http://127.0.0.1:9000/v1/systemone");
      expect(capturedBody.model).toBe("von-1.0.0");
      expect(capturedBody.state).toBe("Refund requested");
      expect(capturedBody.questions.dept.type).toBe("choice");
      expect(resp.answers.dept.type).toBe("choice");
      expect((resp.answers.dept as any).choice).toBe("billing");
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("supports decide helper", async () => {
    const mockFetch = async () => ({
      ok: true,
      json: async () => ({
        model: "von-1.0.0",
        answers: {
          decision: {
            type: "choice",
            choice: "refund",
            confidence: 0.88,
            probabilities: { refund: 0.88, tech: 0.12 },
          },
        },
        usage: { input_tokens: 15, output_tokens: 8 },
      }),
    });

    const orig = globalThis.fetch;
    globalThis.fetch = mockFetch as any;

    try {
      const client = new VonClient();
      const ans = await client.decide("Charge me twice!", ["refund", "tech"]);
      expect(ans.choice).toBe("refund");
      expect(ans.confidence).toBe(0.88);
    } finally {
      globalThis.fetch = orig;
    }
  });
});
