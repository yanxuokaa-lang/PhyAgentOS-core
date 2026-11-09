# Care Desk Live — MongoDB Change Streams × Jev

[![Read the 2-minute explainer](https://img.shields.io/badge/%E2%96%B6%20Read%20the%202--minute%20explainer-0b8f47?style=for-the-badge&labelColor=14211a)](https://qiaohaojie.github.io/Jev-MongoDB/public/explainer.html)

[![Care Desk Live — every card is one customer message, sorted the moment it lands](public/explainer-hero.gif)](https://qiaohaojie.github.io/Jev-MongoDB/public/explainer.html)

**New here? [Start with the picture book.](https://qiaohaojie.github.io/Jev-MongoDB/public/explainer.html)** No jargon, no code — what it does and
why a third of a second matters, in about two minutes.

---

A real-time FMCG customer-care triage demo. A customer message lands in MongoDB, a
**change stream** wakes a worker, **Jev** (TypeSafe's System One model) makes four typed
judgments in one ~300 ms call, the verdict is written back, and a **second change stream**
pushes it to every open dashboard. No polling. No refresh. No queue.

```
Browser ──POST──▶ Express ──insertOne──▶ MongoDB Atlas (messages)
                                            │
                     change stream #1 (insert)
                                            ▼
                                     Classifier worker ──▶ Jev: category · sentiment · urgency · safety
                                            │
                                  updateOne {status:"classified"}
                                            ▼
                                       MongoDB Atlas
                                            │
                  change stream #2 (insert + update, fullDocument: "updateLookup")
                                            ▼
                         Express ──Server-Sent Events──▶ Dashboard (DOM updates)
```

## Run it

You need three things:

1. **Node 20+**
2. A **MongoDB Atlas** cluster — the free M0 tier is fine. Change streams need a replica
   set, and every Atlas cluster is one. A local standalone `mongod` will **not** work.
3. A **TypeSafe API key** — <https://typesafe.ai>

```sh
git clone https://github.com/qiaohaojie/Jev-MongoDB.git
cd Jev-MongoDB
cp .env.example .env      # fill in TYPESAFE_API_KEY and MONGODB_URI
npm install
npm start                 # → http://localhost:3000
```

The server exits with a readable message if either variable is missing.

If Atlas refuses the connection, add your current IP under **Atlas → Network Access**.

Data lives in database `jev_fmcg_demo`, collection `messages` (override with `MONGODB_DB`).
The **Reset demo data** button empties only that collection.

`npm run try "some message"` calls Jev directly, without MongoDB — handy for testing wording.

## Use it

| Area | What it does |
|---|---|
| **01 Customer says…** | Type or click an example, press **Send** (⌘↵). The stopwatch shows click → classified-on-screen time. |
| **02 Simulate traffic** | Inserts realistic messages at 1–8 per second for 30 s. |
| **Pipeline strip** | A dot travels through the seven hops for every real event. Dots take the category colour once Jev has answered. |
| **03 Live feed** | One card per MongoDB document. Arrives as *"Jev is reading"* (insert event), then gets stamped with the verdict (update event). |
| **04 Topics** | Live counters per category. |
| **Throughput / Sentiment** | Inserts per second over the last minute; mood mix from Jev's sentiment score. |
| **05 Raw change events** | The actual change-stream events: op type, document id, updated fields. |
| **KPIs** | Total, average Jev latency, average insert→verdict time (server clock), safety escalations, human-review count. |

## The ten categories

Product Quality · Packaging · **Safety & Health** · Delivery & Availability · Pricing & Promotions ·
Ingredients & Nutrition · Sustainability & Ethics · Praise · Ideas & Suggestions · Other.
Each has a plain-English definition in `src/categories.js`; that text *is* the Jev criteria.
Edit it and restart to change behaviour — no retraining, no prompt engineering.

## The four judgments (one Jev request)

| Question | Primitive | Used for |
|---|---|---|
| Main topic | **Choice** (10 options) | Category, routing team, probability bars |
| How the customer feels | **Score** (5 levels) | Mood emoji, sentiment mix |
| How fast to respond | **Score** (4 levels) | Urgency meter |
| Could a person have been harmed? | **Noul** (yes/no probability) | Safety escalation |

Policy lives in code (`src/classifier.js`):
- `escalate` = safety probability ≥ 0.5 **or** category is Safety & Health.
- `needsReview` = category confidence < 0.7 → route to a human.

## Files

```
src/server.js       Express API, change stream #2 → SSE, traffic simulator
src/worker.js       change stream #1 → Jev → updateOne
src/classifier.js   Jev questions + escalation/review policy
src/categories.js   taxonomy (labels, colours, teams, Jev criteria)
src/samples.js      simulator messages
src/env.js          startup check for required environment variables
public/             dashboard (plain HTML/CSS/JS, no build step)
public/explainer.html        the plain-English explainer page
```

## Heads up: this is a demo, not a service

It is built to be read and recorded, not deployed. There is **no authentication, no rate
limiting and no CSRF protection**, and `POST /api/reset` wipes the collection for anyone who
can reach it. Run it locally. If you do put it on a network, put it behind your own auth.

The product names in `src/samples.js` are invented; any resemblance to a real brand is
coincidental.

## License

MIT — see [LICENSE](LICENSE).

The bundled TypeSafe agent skill under `.agents/skills/typesafe-ai/` is MIT-licensed by
TypeSafe AI and carries its own LICENSE file.
