# Jev plays Balatro

A Balatro mod and server-side controller that give [TypeSafe's Jev](https://typesafe.ai/) two decision loops:

- A run planner chooses a hand focus, spending posture and next improvement.
- A tactical player chooses cards, discards, purchases, consumables and other actions against that plan.

The mod builds on [BalatroBot](https://github.com/coder/balatrobot). It supplies structured game state and available actions, not screenshots. Jev chooses every gameplay move. The game remains responsible for executing them. There is no full-score calculator, and hidden card identities and future draws are not supplied.

**Experiment complete. No winning run was demonstrated.** The best run reached ante 8's Big Blind, scoring 73,386 against a 75,000 target. Jev never reached the ante 8 boss. The controller, knowledge quizzes and playtest results are preserved here, including the failed attempts.

## Run it

The deployment scripts preserve the original Linux setup, not a portable installer. They require the controller hostname `igor-server` and use `desktop` as both a hostname and an SSH alias for remote play. Adapt the host checks and routing before using another setup. Desktop startup and live play are tested. Server startup remains untested.

Run commands from this repository on server. The selected machine needs Steam, Balatro, Proton and a graphical session. The installer currently expects Balatro in Steam's default library. Python 3.11 or newer is enough for the controller, with no Python packages to install. You need your own Balatro installation and TypeSafe API key. Game files and credentials are not included.

The gitignored `.env` holds:

```dotenv
BALATRO_TARGET=server
TYPESAFE_API_KEY=your-key
```

After installing Balatro through Steam:

```sh
scripts/balatro setup
scripts/balatro launch
scripts/balatro inspect
scripts/balatro play
```

Setup creates a separate game copy, mod set and save directory under `~/.local/share/balatro-jev`. It does not launch the game or copy your existing progress. Launch opens that copy. Play starts one White Stake run from the menu and stops at victory or defeat. The default deck is Red; `--deck` selects another vanilla deck.

For desktop, change `BALATRO_TARGET` in `.env` or override it per command:

```sh
BALATRO_TARGET=desktop scripts/balatro setup
BALATRO_TARGET=desktop scripts/balatro launch
BALATRO_TARGET=desktop scripts/balatro play
```

The controller and API key stay on server. Desktop mode connects through an SSH tunnel. Only one target uses local port `12346` at a time. Stop the old target before switching.

```sh
scripts/balatro play --seed JEVTEST
scripts/balatro play --deck CHECKERED --seed JEVCHECK
scripts/balatro play --resume
scripts/balatro stop
```

`--resume` explicitly takes over an active run and cannot be combined with `--seed` or `--deck`. Without it, the controller refuses to overwrite one. Ctrl+C stops the controller, but an already-sent game action may finish. `stop` closes the isolated game and its desktop tunnel when applicable.

Decisions, supplied state, probabilities and usage are recorded in gitignored `logs/`. A run defaults to at most 1,000 action attempts and 1,000 API requests. Use `--max-steps` and `--max-calls` to change those bounds. These are request limits, not dollar limits.

## What Jev knows

The [quiz report](evaluation/REPORT.md) found patchy native Balatro knowledge and much stronger results with explicit rules. The controller therefore supplies a rules reference. Arithmetic belongs in code, not in Jev's memory.

Run the quizzes without launching Balatro:

```sh
scripts/balatro quiz
scripts/balatro quiz --dataset transfer
```

Both use pinned model `jev-1.13.0` by default. `--model` selects another model for either play or quizzes.

## Playtests

Red Deck, White Stake, `jev-1.13.0`. These are smoke tests, not a win-rate estimate.

| Controller | Seed | Result | Discards used |
| --- | --- | --- | --- |
| Baseline | `JEVTEST` | Lost at ante 4's Big Blind | 0 |
| Tuned | `JEVTEST` | Lost at ante 5's Eye | 18 |
| Tuned | `JEVNEXT` | Lost at ante 3's Needle | 27 |

The tuned `JEVTEST` run resumed once after an API timeout. Score prediction remains weak: `JEVNEXT` played its only hand for 372 against a 2,000 target with two discards left.

Further prompt experiments lost twice at ante 1's Pillar on `JEVTHIRD` (278/600 and 493/600), then at ante 4's Tooth on `JEVFOUR` (9,130/10,000). `JEVFOUR` used 42 discards and resumed once with revised prompts after a pointless joker-reordering loop. These results do not establish an improvement in win rate.

On Checkered Deck, White Stake, `JEVCHECK` lost at ante 5's Water (18,703/22,000), with 31 accepted discards. It resumed after an API 503 at ante 4 with clearer item details and sale-slot arithmetic. Jev kept its starter Joker lineup despite stronger visible offers. This is a separate deck experiment, not an improvement established on Red Deck.

A replay with explicit replacement offers lost at ante 2's Big Blind (984/1,000), before filling its Joker slots. It chose unscaled scoring over an immediately useful starter. Saved-state tests of a separate card-benefit assessment improved several shopping choices, but do not establish better run results.

A third attempt used those assessments and lost at ante 4's Mark (3,397/10,000). It resumed after the loop guard stopped pointless Joker reordering, with more explicit card effects and a separate ordering judgment. It escaped the loop but still played weak hands against face-down cards.

A fourth attempt ran that revised policy from the start without intervention. It kept Foil Odd Todd and reached ante 6's Tooth, losing at 26,292/40,000 with $152 unspent and 32 accepted discards.

With clearer card-cycling and shop-search guidance, a fifth attempt also lost at ante 6's Tooth (30,016/40,000). It used 29 accepted discards, rerolled 20 times and upgraded Flush, but passed up Card Sharp and Blackboard. It finished with $6. More spending did not solve build selection.

A sixth attempt lost at the same boss (29,666/40,000), despite upgrading Flush twice. It also used The Moon to add Clubs to its Hearts-and-Spades deck, reducing Flush consistency.

A seventh attempt used clearer consumable target descriptions and kept the deck to Hearts and Spades. It lost at the same boss with 35,438/40,000. The final lineup still had no X Mult Joker.

An eighth Checkered attempt used separate Joker judgments and persistent scoring history. It lost at the same boss with 36,113/40,000 and $27 unspent. It upgraded Flush twice but again passed up Card Sharp with full Joker slots. Better open-slot purchases had not solved replacements.

A ninth attempt used completed-replacement comparisons. It made several trades but lost at ante 6's Small Blind with 17,998/20,000 and $94 unspent. It opened no booster packs after the first Buffoon Pack. It also chose plain cards over enhanced Fives that would activate Odd Todd within the same Flush.

A tenth attempt separated play ranking from long-term planning. It lost at ante 5's Small Blind with 8,563/11,000 and $45 unspent. It omitted an enhanced Queen from a Flush, then twice chose a lone Ace over an available pair of Queens. The stronger options reached Jev; missing action coverage did not explain those choices.

An eleventh attempt listed every held card when comparing plays. It kept Foil Baron but lost at ante 5's Water with 16,037/22,000 and $67 unspent. It opened no booster packs after the first Buffoon Pack. Packs and vouchers were available actions but had not received the separate purchase assessments.

A twelfth attempt added those assessments and lost at ante 6's Big Blind with 25,708/30,000 and $28 unspent. Jev opened more packs, but Flush stayed at level 1 and the final Joker lineup still lacked X Mult. It also missed useful card-triggered bonuses within Flushes.

A thirteenth attempt ran the same policy without intervention. It beat ante 6's Tooth and ante 7's Arm, then lost at ante 8's Big Blind with 73,386/75,000 and $60 unspent. Spare Trousers had grown to +58 Mult, but the final lineup still lacked X Mult. This is the furthest completed run, not an ante 8 boss win.

A fourteenth attempt used clearer edition descriptions and retained Foil Baron. It lost at ante 6's Tooth with 38,770/40,000 and $54 unspent. Flush reached level 3, but Jev repeatedly discarded Kings that could activate Baron.

A fifteenth attempt clarified held-card value in discard decisions. It lost at ante 6's Tooth with 37,510/40,000 and $19 unspent. Jev sold Foil Baron for Lusty Joker while retaining the plain +4 Mult Joker. The replacement comparison happened only after it had chosen which Joker to sell.

A sixteenth attempt compared replacements before shortlisting sales. It kept Foil Baron but lost at ante 6's Big Blind with 28,447/30,000 and $38 unspent. Flush stayed at level 1. Jev rejected Turtle Bean's extra hand size and left the final shop without another upgrade.

A seventeenth attempt judged pack searches across the whole reveal. It opened five Celestial Packs, raised Flush to level 5 and beat ante 6's Tooth. It lost at ante 7's Big Blind with 41,952/52,500 and $11 unspent. Jev retained Foil Baron, but also kept the plain +4 Mult Joker over later Raised Fist and Mystic Summit offers. More upgrades did not produce a winning build.

An eighteenth attempt grouped plays by hand type. It lost at ante 6's Tooth (29,330/40,000), with Flush at level 2 and $64 unspent. The controller paused at an ante 6 shop after a prompt-size guard fired, then resumed after a JSON encoding fix.

A nineteenth attempt used the hand-family ranking and compact JSON encoding throughout. It bought Card Sharp and reached ante 8's Big Blind, losing at 29,460/75,000 with $46 unspent. After one Flush, it played Straight Flush, Two Pair and Straight, so none of those later hands activated Card Sharp.

A Plasma Deck trial on `JEVPLASMA` paused after ante 1's Big Blind because TypeSafe returned `503 model_unavailable`. It later resumed with revised Joker judgments and lost at ante 2's Goad, scoring 1,962/3,200. That resumed run used the old spending planner and had no persistent scoring history.

A fresh Plasma run used persistent scoring history and the revised spending planner throughout. It also lost to ante 2's Goad, at 2,306/3,200. Jev discarded a valid Full House containing a debuffed Nine. The hand was offered correctly, but the final decision rejected it.

Saved-state replays compared the old item assessment with separate Joker contribution and activation judgments, using normal and reversed action order. The revised player bought Card Sharp instead of Chaos in both open-slot shop replays. It still chose Abstract over unscaled Flash Card and rejected ordinary cards that would dilute Checkered Deck. It still missed Blackboard. These decision checks do not establish a better win rate.

## Limits and troubleshooting

- This is an experimental player, not a demonstrated winning bot. Quiz scores are not win rates.
- The planner refreshes at phase changes, material build changes, changed blinds, shop budgets and offers. The loops do not run concurrently because Balatro waits for decisions.
- Spending decisions compare measured plays from the last three blinds with the next blind and the next ante's public baseline requirements. The history survives shop actions but starts empty when a controller session resumes. Past scores are not forecasts, and future boss identities remain unknown. The baseline requirements follow the [wiki's ante table](https://balatrowiki.org/w/Blinds_and_Antes); the spending guidance follows the distinction between immediate strength, income and boss preparation in [PC Gamer's strategy guide](https://www.pcgamer.com/balatro-tips/).
- Actions are shortlisted by purpose before a final comparison, so joker orders cannot crowd out all discards or purchases. Joker and consumable sales have separate shortlists because they free different slots. Large groups use tournaments with at most 128 options per question. Every initial candidate is considered, but a good move can still be dropped within its group.
- Play shortlists first compare alternatives within game-recognized hand types, then compare the survivors across types. These comparisons use current mechanics without the planner's hand focus or spending posture. The final play-versus-discard decision still receives the plan and measured history. Replays of eight positions in both action orders chose available pairs of Queens over High Cards more consistently, but still missed an enhanced card within a Flush. These checks do not establish a better win rate.
- Hand names and nominal base scores are game-derived. Nominal scores omit the effects named in their labels and are not full score predictions. Play options bind public card effects to played or held positions and list every unselected card, including ordinary cards, so Jev can weigh scoring against cycling and held-card effects. Saved-state comparisons across seven positions in both action orders corrected some missed card bonuses, but still chose weak High Cards. These checks do not establish a better win rate.
- Discard guidance distinguishes the scoring hand from useful held cards. An off-suit card is not automatically disposable when its held effect helps. Jev still chooses the entire discard selection and can misjudge that tradeoff.
- Plasma Deck receives its balancing rule instead of ordinary final-scoring guidance. Blind targets come from the game and are not doubled again. This supplies mechanics, not calculated play scores.
- Item options bind public suit/rank, editions, seals and rarity to the selected card. Joker editions are described as independent of the printed ability's activation. Consumable uses also bind each target's existing effects so Jev can weigh what changes or gets replaced. Pack Planets are described as immediate hand upgrades, not extra playing cards. With full Joker slots, sale options repeat visible replacement offers for comparison; selling and acquiring remain separate Jev decisions.
- In shops and packs, Jev judges each Joker's current contribution separately from what this deck needs to activate it. Other offered cards and vouchers receive a practical-benefit judgment. Unopened packs receive a search-usefulness judgment about the whole reveal and selection, not a single random card. A pack can offer a useful choice even when most individual contents would not help. No result is guaranteed. The final decision still weighs cost and alternatives. These fallible judgments do not filter or force actions. Later prompts carry the selected judgments and their probabilities; complete distributions remain in the API audit.
- Replays of eight saved shops in both action orders retained Mad Joker, Foil Baron and Uranus purchases and low-cash exits. The revised pack judgment spent in the last shop instead of leaving, but still favored Standard Packs and sometimes sold a Joker instead of opening a Celestial Pack. These checks do not establish better play or win rate.
- With full Joker slots, Jev compares visible replacements for every legal Joker sale that opens a slot, before shortlisting a sale. Each comparison judges a completed exchange. The final decision still weighs money and other actions. Selling and acquiring remain separate choices, and the comparison can be wrong. Replays of eight saved shops in both action orders preserved the control purchases but did not consistently protect Foil Baron. These checks do not establish a better win rate.
- Before committing a hand, Jev judges its strength and whether a proposed Joker reorder actually helps. The proposed order includes each Joker's public effects. These are fallible judgments, not a score calculator or a veto.
- The mod hides face-down identities and draw order. It supplies public deck-viewer suit/rank counts, excluding Stones from those tallies. Unplayed counts retain the viewer's uncertainty about face-down draws. Hand-reordering actions and some legal Negative Joker purchases with full slots remain unsupported.
- Joker and consumable sales are available inside packs so Jev can make room for replacements. Pack sales use the vanilla game callback because BalatroBot's sale-completion check excludes that phase.
- A stale decision is rejected before acting. Other action failures stop the controller instead of guessing whether a move happened.
- `scripts/balatro logs` shows game startup errors. `inspect` checks the companion protocol without making Jev calls.
- Setup checks the known Balatro build and pinned mod downloads. A different game build needs checking before changing `deploy/runtime.lock`. Locally installed Proton is reused, not bundled.

## Checks

```sh
scripts/check
```

These offline checks do not install dependencies, contact Jev or launch the game. They do not replace live game testing.
