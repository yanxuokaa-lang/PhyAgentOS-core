import type {
  Answer,
  ChoiceAnswer,
  ChoiceQuestion,
  NoulAnswer,
  NoulQuestion,
  Question,
  ScoreAnswer,
  ScoreQuestion,
  SystemOneResponse,
  VonClientOptions,
} from "./types.js";
import { choice, noul, score } from "./primitives.js";

export class VonError extends Error {
  public status?: number;
  public details?: unknown;

  constructor(message: string, status?: number, details?: unknown) {
    super(message);
    this.name = "VonError";
    this.status = status;
    this.details = details;
  }
}

export class VonClient {
  public baseURL: string;
  public apiKey?: string;
  public timeout: number;

  constructor(options: VonClientOptions = {}) {
    const envBase = typeof process !== "undefined" ? (process.env?.VON_BASE_URL || process.env?.TYPESAFE_BASE_URL) : undefined;
    this.baseURL = (options.baseURL || envBase || "http://localhost:8000").replace(/\/$/, "");

    const envKey = typeof process !== "undefined" ? (process.env?.VON_API_KEY || process.env?.TYPESAFE_API_KEY) : undefined;
    this.apiKey = options.apiKey || envKey || undefined;

    this.timeout = options.timeout ?? 30000;
  }

  /**
   * Evaluates state and questions via System One wire protocol (POST /v1/systemone).
   */
  async systemOne({
    state,
    questions,
    model = "von-1.0.0",
  }: {
    state: unknown;
    questions: Record<string, Question>;
    model?: string;
  }): Promise<SystemOneResponse> {
    const url = `${this.baseURL}/v1/systemone`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }

    const payload = {
      model,
      state,
      questions,
    };

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    try {
      const res = await fetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new VonError(
          `Von server error (${res.status}): ${errText}`,
          res.status,
          errText
        );
      }

      return (await res.json()) as SystemOneResponse;
    } catch (err: any) {
      if (err.name === "AbortError") {
        throw new VonError(`Von request timed out after ${this.timeout}ms`);
      }
      if (err instanceof VonError) throw err;
      throw new VonError(`Von network failure: ${err.message}`);
    } finally {
      clearTimeout(timer);
    }
  }

  /**
   * Convenience helper for discrete categorical choice classification.
   */
  async decide(
    state: unknown,
    choices: Record<string, string | null> | string[],
    instructions = "Which option best describes the state?",
    model = "von-1.0.0"
  ): Promise<ChoiceAnswer> {
    const q = choice(instructions, choices);
    const resp = await this.systemOne({
      state,
      questions: { decision: q },
      model,
    });
    return resp.answers["decision"] as ChoiceAnswer;
  }

  /**
   * Convenience helper for binary verification (Noul probability).
   */
  async judge(
    state: unknown,
    instructions: string,
    posCriteria?: string,
    negCriteria?: string,
    model = "von-1.0.0"
  ): Promise<number> {
    const criteria =
      posCriteria || negCriteria
        ? { pos: posCriteria, neg: negCriteria }
        : undefined;
    const q = noul(instructions, criteria);
    const resp = await this.systemOne({
      state,
      questions: { verdict: q },
      model,
    });
    return (resp.answers["verdict"] as NoulAnswer).noul;
  }

  /**
   * Convenience helper for ordinal multi-level rating (Score).
   */
  async rate(
    state: unknown,
    levels: string[] | Record<string, string>,
    instructions = "Rate the severity or level:",
    model = "von-1.0.0"
  ): Promise<ScoreAnswer> {
    const q = score(instructions, levels);
    const resp = await this.systemOne({
      state,
      questions: { rating: q },
      model,
    });
    return resp.answers["rating"] as ScoreAnswer;
  }
}

/** Drop-in alias for TypeSafe Jev SDK migration */
export const TypeSafeClient = VonClient;
