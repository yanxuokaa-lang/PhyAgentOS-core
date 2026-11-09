import type { ChoiceQuestion, NoulQuestion, ScoreQuestion } from "./types.js";

/**
 * Build a discrete categorical Choice question.
 */
export function choice(
  instructions: string,
  criteria: Record<string, string | null> | string[]
): ChoiceQuestion {
  const normCriteria: Record<string, string | null> = Array.isArray(criteria)
    ? Object.fromEntries(criteria.map((c) => [c, null]))
    : criteria;

  return {
    type: "choice",
    instructions,
    criteria: normCriteria,
  };
}

/**
 * Build a binary verification Noul (Yes/No probability) question.
 */
export function noul(
  instructions: string,
  criteria?: { pos?: string; neg?: string } | null
): NoulQuestion {
  return {
    type: "noul",
    instructions,
    criteria: criteria ?? null,
  };
}

/**
 * Build an ordinal multi-level Score question.
 */
export function score(
  instructions: string,
  criteria: string[] | Record<string, string>
): ScoreQuestion {
  return {
    type: "score",
    instructions,
    criteria,
  };
}
