// Run with `npm run demo`. Needs TYPESAFE_API_KEY in the environment.
import { APIError, choice, noul, score, TypeSafeClient } from "../src";

const client = new TypeSafeClient({ logLevel: "info" });

const models = await client.models.list();
console.log("Available models:", models.map((m) => m.name).join(", "));

const ticket = {
  subject: "Charged twice this month",
  body: "Hi, I see two charges of $49 on my card for August. I only have one account. Please fix this ASAP, I'm pretty frustrated.",
};

try {
  const { answers, usage } = await client.systemOne({
    state: ticket,
    questions: {
      isBilling: noul("Is this ticket about billing?"),
      sentiment: choice("What is the customer's tone?", {
        calm: null,
        frustrated: null,
        angry: null,
      }),
      urgency: score("How urgent is this ticket?", ["can wait", "this week", "today", "right now"]),
      refundRisk: score("How likely is the customer to demand a refund?", [
        "unlikely",
        "possible",
        "likely",
      ]),
    },
  });

  // Every answer is typed by the question that produced it.
  const { isBilling, sentiment, urgency, refundRisk } = answers;
  console.log("billing?    ", isBilling.noul.toFixed(2));
  console.log(
    "tone        ",
    sentiment.choice,
    `(${sentiment.probabilities[sentiment.choice].toFixed(2)})`,
  );
  console.log("urgency     ", urgency.score.toFixed(2), "on a 0-3 scale:", urgency.legend);
  console.log(
    "refund risk ",
    refundRisk.score.toFixed(2),
    `(${refundRisk.confidence.toFixed(2)} confidence)`,
  );
  console.log("tokens      ", usage.input_tokens, "in /", usage.output_tokens, "out");
} catch (err) {
  if (err instanceof APIError) {
    console.error(`API error ${err.status} (request ${err.requestId ?? "unknown"}):`, err.body);
  } else {
    throw err;
  }
}
