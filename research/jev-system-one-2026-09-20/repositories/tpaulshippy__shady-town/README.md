# Shady Town

A social-deduction party game for the living room TV. Humans play, the TV moderates.

> Name note: this is an original game inspired by the classic 1986 social-deduction
> party format (often called Mafia / Werewolf). "Shady Town" is our own name, our own
> wording, and our own code — no affiliation with, and no use of, any commercial
> Mafia or Werewolf board game, card game, or video game.

## The pitch

Shady Town turns your living room into a detective show.

Everyone plays — no one has to sit out to be the moderator. You act, argue, bluff,
and vote on your phones. The TV shows live suspicion meters next to each player's
name, like a sports broadcast.

Did Ben just lie about being the doctor? The meters twitch. Is the group going in
circles? The game nudges you: "new clue needed" or "time to vote."

No reading a 20-page rulebook. No older kid stuck running the game instead of
playing. Rounds stay fast, quiet kids get spotlighted by the meters instead of
shouted over, and parents get a built-in excuse to talk about bluffing vs. lying
afterward.

Bring 6–10 people, a TV, and 30 minutes. It handles the awkward hosting parts so
you just get the yelling, laughing, and accusing your teenager of being very shady.

## How it works

Here's a full game, start to finish:

**Setup — 2 minutes.** One person opens Shady Town on the TV. Everyone else joins
on their phone with a name — no app install, just a link. You pick how many secret
troublemakers there are. Usually 2 troublemakers in a group of 8. Everyone gets a
secret role on their phone: townsfolk, doctor, detective, or troublemaker. Only you
see yours.

**Night — 30 seconds.** The TV goes dark; everyone closes their eyes except when
tapped. The troublemakers silently pick someone to take out. The doctor silently
picks someone to save. The detective silently checks one person. Your phone just
shows one big button when it's your turn, then goes back to sleep. Nobody has to
memorize what to do — it taps you.

**Day — the fun part.** The TV announces what happened overnight: "Pat didn't wake
up." Then discussion starts. This is just talking — accusing, defending, making up
stories.

On your phone you do three simple things when you want:

1. Say what you claim — "I'm the doctor, I saved Ana"
2. Vote who you suspect
3. React — agree, doubt, laugh it off

The TV shows a meter next to every player still in the game. Clear on the left,
Busted on the right. When two people vote for Ben after his doctor claim doesn't
add up, his meter slides toward Busted for everyone to see. When Ana has barely
spoken and has no votes, she stays Clear.

It also watches the room mood two ways:

- "Someone's probably bluffing" — lights up when stories contradict each other
- "You're going in circles" — lights up after minutes of repeat arguments with no
  new info, and suggests: take 60 more seconds, then vote

Nobody is running this. No human moderator deciding who looks guilty. The meters
just reflect what the whole room has said and done so far.

**Voting and elimination.** When the room is ready, the TV calls a vote. Everyone
taps one name. Most votes is out — they reveal their role, big dramatic moment,
then they're on the jury. They can still watch and chat but can't vote.

**Repeat until it ends.** Night, day, vote. 3–4 rounds, about 25 minutes total.
Either the troublemakers outnumber the town, or the town finds them all. The TV
does a recap at the end: the biggest bluff, the closest vote, who fooled everyone
longest.

**Why it feels different from the classic version:**

- No one sits out to host
- Shy players matter because votes and claims move meters, not just loud voices
- Games don't stall — it notices the loop and pushes you to vote
- No fights about rules — it remembers who voted for whom and what everyone claimed

## For developers

One fast structured judgment per round: game state in, suspicion levels out.
Decisions and thresholds stay in code. Built on TypeSafe's Jev via
`ruby_llm-typesafe` (`jev-latest`).

```bash
bundle install
bundle exec ruby bin/moderate   # mock mode, no key needed
bundle exec rspec               # tests
```

Live mode:

```bash
export TYPESAFE_API_KEY=...
bundle exec ruby bin/moderate
```

Layout: `lib/shady_town/game_state.rb` (round, alive, votes, claims, events),
`lib/shady_town/evaluator.rb` (per-player Clear/Shady/Busted + bluff/stall signals),
`bin/moderate` (demo), `spec/` (offline tests with injected fake answers).
