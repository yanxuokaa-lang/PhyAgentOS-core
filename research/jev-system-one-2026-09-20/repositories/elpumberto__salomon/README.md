# Salomón

An experiment in analysing long content, whole books to begin with, using [Jev](https://docs.typesafe.ai) and models like it: ones that answer closed questions with probabilities instead of writing text.

What came of it is to be seen, and weighed another way, at [salomon.pumberto.com](https://salomon.pumberto.com).

It is an experiment, not a product. How a book gets from a file to a valuation, who does what on the way and what it costs is in [docs/books/pipeline.md](docs/books/pipeline.md). The repo is also the register of what was run: when, on which text, under which rules and with what result, under [records/](records/README.md).

## Books

No book goes in the repo, nor anything made from one: `books/` is ignored whole. A book that is not of the list is somebody's, and is treated so without being asked to: its notes are only taken by providers that do not store what they are sent, and what is recorded of it keeps the hash of its text and neither the name nor the hash of the file it came from. An EPUB with copy protection is not read. The ones the experiment starts from are Project Gutenberg's, listed in `gutenberg.json` with the sections of each that are the story, and whether it is a book to judge or one a passage is taken from to set others against, and

    npm install
    npm run fetch

brings each of them to `books/` as EPUB and as plain text. Any other `.epub` or `.txt` can be read from wherever it is; an EPUB under DRM cannot.

## Normalizing

    npm run normalize -- books/king-solomons-mines.epub

reads a book and writes it to `books/normalized/` as JSON: title, author, language and the book's sections, each with its title and its paragraphs as plain text. It prints what is in the book and a rough estimate of what sending it to Jev would take; `--sections` lists every section.

In an EPUB the sections are the ones its table of contents points at, or its headings when it has none. In plain text they are guessed from the lines that read like a chapter's heading. Project Gutenberg's licence comes off both.

## Reading notes

Jev takes in some 32,000 tokens a call, so it never sees a whole book: a chapter at most. What it cannot see, a language model reads ahead of it and writes down, a section at a time and in order, carrying what a reader would remember:

    npm run notes -- books/king-solomons-mines.epub --from 4

says what taking the notes would cost and asks nothing; with `--go` it takes them, stopping at `--max-usd` (0.25 unless told). `--from` and `--to` are section numbers as `normalize --sections` lists them. `--model` is any model of OpenRouter's that can answer in a given JSON shape; left out, it is Gemini 3.1 Flash-Lite, which [nine were tried](docs/books/notes-experiments.md) to choose. OpenRouter is asked for the cheapest of a model's providers first, and `--sort`, `--only` and `--ignore` say otherwise. The notes go to `books/notes/`, a file per book and model, saved after every section: a run that stops goes on from there when run again, and `--redo` starts over. `--show` prints them to be read. A run leaves its record under `records/`, whether it gets to the end or breaks, and `npm run records -- king-solomons-mines` sets a book's records side by side.

For each section the model says whether it belongs to the work or stands around it, what happens in it, what changes for each character, and which of the story's open questions it opens, moves or closes. A second call rewrites what a reader knows so far, which is what the next section is read in the light of, and is asked again if that runs long or lets go of the story. Once the book is read, a last call looks again, with the whole of it in view, at the threads that were left open. The code keeps the cast and the ledger of threads. The model takes notes and judges nothing: it is told to go by the text alone and to leave out what it remembers of the book and what it thinks of it. Judging is Jev's.

## Asking Jev

    npm run judge -- books/king-solomons-mines.epub

judges a book the way books are valued: twelve passages of 3,000 words, spread over its story and cut across its chapters, each put to Jev with fourteen questions about what a reader, an editor or a teacher would do with it. It shows the questions as they would be asked, the passages and about what it would cost, a quarter of a cent a book, and sends nothing; with `--go` it asks, a call a passage, and leaves a record under `records/`. Jev is given the text alone, with no title nor author. The story of a book of the list is the sections `gutenberg.json` says; of any other, `--sections 3-22`, numbered as `normalize --sections` lists them.

    npm run value

says what the books judged so far are worth, from the records and asking nothing: their literary merit and how good a read they are, by the rules of [src/value.ts](src/value.ts), which are arithmetic on Jev's answers and have a hash of their own, with what judges nothing beside them: how even the book is, what it reads like and whom it is written for. With the name of a book's folder under `records/books/`, that book in full.

Told how, `judge` is a trial of something and is recorded as one: `--questions` names another set of [src/questions.ts](src/questions.ts), a section is then a passage, `--pieces 1000` cuts each in pieces of about as many words, `--across` cuts them over the sections as one text, `--together` sends a range of sections as one text, and `--sample 12` takes as many passages, evenly spread.

How it came to this, from what is known of what makes a book good to the check on books never seen, is laid out in order in [docs/](docs/README.md), with everything that was run and what it cost; the experiments are under [experiments/books/jev/](experiments/books/jev/). What Jev reads well, where it gets stuck and what moves its answers besides the text was [tried on chapters whose answers were known](docs/books/jev-experiments.md). A first valuation, of twenty-nine questions about the qualities of the writing and a panel of passages to set a book against, was set on [ten books of known standing and checked on ten others](docs/books/calibration.md). The twenty then became a bench on which [other questions and other sizes of passage](docs/books/other-ways.md) were tried by one yardstick; the way that did best was checked on twelve books more, and is the one in use. What only the whole book shows, how it is built, how it ends and whose side it takes, is asked of an outline made from the reading notes and of each chapter with the story so far beside it: [what that tells, and what it does not](docs/books/whole-book.md).

## The site

    npm run site

writes `site/data.json` from the records: every book judged the way books are valued, with its valuation and what each answer came to, passage by passage. [site/index.html](site/index.html) is one static page, in Spanish and in English, that reads it: the books on a map, the ranking, the nine answers to weigh another way, which asks nothing of anybody, and a card of each book to share. Nobody can have a book judged from it. What a record cannot say of a book, that the copy judged was a poor one, is in `site/books.json`. `npm run cards` then gives each book a page of its own and a picture of its card in each language, taken by a browser with no window, so that the address of a book shows its card wherever it is pasted. To see it, serve the folder: `python3 -m http.server -d site`. A workflow publishes it from `main`.

## Keys

Two services are paid for, each with a key of yours: [Jev](https://console.typesafe.ai/keys), and [OpenRouter](https://openrouter.ai/settings/keys) for the language models that read a book ahead of it. Copy `.env.example` to `.env` and put them there; git ignores `.env`. OpenRouter lets a key be given a credit limit, which is worth doing.

    npm run test:apis

checks both against the real services: that a made-up key is turned down, that yours is taken, and that each answers a sentence the way the code expects. It prints what that took, which is a few millionths of a dollar.

`npm install` sets a git hook that refuses a commit carrying a key: the value of any in `.env` wherever it turns up, what looks like one, `.env` itself, or a value in `.env.example`.

## Working on it

Node 22.18 or later, which runs the TypeScript as it is. `npm test` runs the tests, none of which touches the network; `npm run check` the types, `npm run lint` Prettier.
