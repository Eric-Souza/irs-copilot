# IRS Copilot

[![CI](https://github.com/Eric-Souza/irs-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/Eric-Souza/irs-copilot/actions/workflows/ci.yml)

Ask a question about your 2025 U.S. federal income tax return and get an answer from **IRS Publication 17 (2025), Your Federal Income Tax**. The answer cites the publication's sections. An agent built on LlamaIndex Workflows can search again or follow the publication's own cross-references ("see *Qualifying Relative*, later") when one section isn't enough. When Pub 17 doesn't cover the question, it says so. A golden set of 80 questions measures what the agent adds over plain RAG and what it costs.

It is the U.S. counterpart of [IRPF Copilot](https://github.com/Eric-Souza/irpf-copilot), which does the same for the Brazilian return. The agent, eval, stores and tracing are the same; the corpus, parser and golden set are new.

```
$ uv run python -m tax.agent "My bank forgave part of my credit card debt and sent me a 1099-C. Is there any way I don't owe tax on it?"

Yes. You have no income from the canceled debt if it's intended as a gift to you [8.3]. Additionally,
you do not include a canceled debt in your gross income in the following situations:
- The debt is canceled in a bankruptcy case under title 11 of the U.S. Code [8.4].
- The debt is canceled when you're insolvent (though you can't exclude any amount of canceled debt
  that is more than the amount by which you're insolvent) [8.4].

tools: search_publication(canceled debt exceptions), cited: 8.3, 8.4, 2 model calls, 7,726 tokens
```

Section 8.4, Exceptions, wasn't in the top 5 for the question. The agent searched again and found it. RAG over sections answers the same question with the gift rule only and says Pub 17 covers nothing else.

## What it shows

- **A parsed corpus with its structure.** `tax/pub17.py` parses the HTML edition of Pub 17's 14 chapters into 356 sections. Each section has its heading path ("Chapter 3. Dependents > Dependents > Qualifying Child > Age Test") and the sections it links to: 285 links in all, from 140 sections. The HTML links each "see ..., earlier" to an anchor, so the cross-references come from the markup, not from parsing prose. A section is one retrieval unit. Long sections are split under their heading, so every node knows what to cite.
- **An agent with two tools.** A LlamaIndex Workflow starts from the same top 5 as the baseline. Before it answers, it may call `search_publication(query)` or `read_section(id)`, up to 4 calls in all.
- **Citations checked by code.** Every `[3.9]` an answer cites must have been retrieved or read in that conversation. Any other citation is dropped from the text and reported.
- **Refusals decided by the model, not a threshold.** Out-of-scope questions still score high in retrieval: median top similarity is 0.708, against 0.782 for answerable questions. That overlap is too large for a cutoff.
- **A golden set checked against the publication.** A test checks that each fact an answer must contain appears in the labeled section's text, so a label can't drift from Pub 17.
- **Chroma and Pinecone behind one retriever,** using the same embeddings and compared on the same queries.
- **Traces and experiments in Phoenix.** Each question is one trace, and each system's eval run is an experiment on the golden set.

## Scope

Pub 17 (2025) has 14 chapters:

- filing information and filing status
- dependents
- withholding and estimated tax
- wages, interest, Social Security and other income
- IRAs
- the standard deduction, taxes and other itemized deductions
- figuring the tax
- the child tax credit

Some topics Pub 17 used to cover in full are now only pointers to other publications: capital gains, the mortgage interest and medical deductions, charitable contributions, and the earned income credit. The golden set's out-of-scope questions cover these, along with state taxes, other years and other countries.

## Eval

`python -m evals.run` asks each golden question to three systems and scores the answers in code. It checks whether the answer states the fact, cites a labeled section, and refuses only when it should. Answers are cached per system and per prompt version, so rescoring costs no quota.

Results on the 80 questions with Gemini 3.5 Flash Lite (`evals/results/run.md`):

| System | Fact right | Multi-hop | Hard-hop | Cites a labeled section | Refuses out of scope | Refuses in scope | Model calls | Tool calls | Tokens |
|---|---|---|---|---|---|---|---|---|---|
| RAG over chunks | 75% | 77% | 33% (2/6) | 43% | 91% | 16% | 1.00 | 0.00 | 3,012 |
| RAG over sections | 84% | 85% | 33% (2/6) | 91% | 100% | 9% | 1.00 | 0.00 | 2,196 |
| Agent over sections | 91% | 92% | 67% (4/6) | 94% | 100% | 4% | 1.21 | 0.21 | 3,491 |

What the answers say:

- **The index still matters most.** Section nodes fix 13 of the chunk baseline's 18 misses and cut tokens by a quarter. Chunks have no headings, so the model often can't tell what a chunk is about and refuses: 11 of the chunk baseline's 18 misses are refusals of answerable questions, three of them the standard deduction.
- **The agent gains more here than in irpf-copilot.** It's 7 points over RAG on sections, against none for the Brazilian manual, at about 60% more tokens. It called a tool on 15 of the 80 questions. It's right on 5 questions that RAG on sections gets wrong. On four of them (n06, c15, and the hard-hop items h03 and h07), a second search found what the first missed. The fifth, m10, took no tool call: the same retrieval with the agent's instructions.
- **It never followed a link.** All 15 tool calls were `search_publication` with a reworded query, never `read_section`, even though Pub 17's links are exact. The reworded search found the hop section each time it mattered. On the two hard-hop misses, h02 and h06, the agent made no tool call at all. It answered from the first section and stopped.
- **The remaining misses are retrieval and wording.** On c06 (a watch for years of service) and m01 (a mother as qualifying relative), the sections index doesn't retrieve the labeled section, and both systems on it refuse. The chunk index does retrieve it, and the chunk baseline gets m01 right. c17 is wording: the answer says to report tips "on the same line as your regular pay", and the fact expects "part of your pay".
- **Out-of-scope refusals are right for both systems on sections.** The agent searched again on 8 of the 11 before refusing, so a refusal costs about two model calls.

Six hard-hop items are too few to put a number on the agent's gain there. They show where it comes from.

Retrieval alone (`python -m evals.retrieval`, top 5 on the 69 answerable questions):

| Index | hit@1 | hit@5 | MRR@10 | Multi-hop, both @5 | Hard-hop, second @5 | Context at 5 |
|---|---|---|---|---|---|---|
| sections | 74% | 94% | 0.83 | 92% | 0% | 7,150 chars |
| chunks | 64% | 91% | 0.75 | 77% | 50% | 10,949 chars |

What retrieval says:

- **Section nodes rank the right section first more often, with a third less context.**
- **The second section of most multi-hop pairs is already in the top 5,** so following links has less to gain than expected.
- **Hard-hop items are where links matter.** These are 6 multi-hop pairs where the hop section is outside the sections index's top 5, picked by running retrieval. Fixed-size chunks bring half of those hop sections anyway, because a chunk can run across the boundary into the next section.

On Pinecone (`--pinecone`) the scores are identical, and 77 of 80 top-5 lists are the same. Pinecone's median query takes about 200 ms from here, against 3 ms for Chroma on disk. Both are well under the second a model call takes.

## Tracing with Phoenix

With `PHOENIX_COLLECTOR_ENDPOINT` set (`http://localhost:6006` for a local `phoenix serve`), [OpenInference](https://github.com/Arize-ai/openinference)'s LlamaIndex instrumentation sends each question to [Phoenix](https://github.com/Arize-ai/phoenix) as one trace (`tax/tracing.py`). A trace holds:

- the Workflow's steps
- the retrievals
- the model calls, with their prompts, tool calls and tokens
- a span per tool call, with the retrieval it made nested under it

Eval questions are tagged with the system, the golden id and the kind.

`python -m evals.phoenix` uploads the golden set as a dataset and logs each system's cached answers as an experiment. The scoring is the same code as the eval: fact, refusal, citations and tool calls. You can compare the three systems question by question without a model call.

## Stack

| Part | Choice |
|---|---|
| Corpus | IRS Publication 17 (2025), HTML edition from irs.gov (`data/p17.html`) |
| Framework | LlamaIndex 0.14: `VectorStoreIndex`, Workflows, `FunctionTool` |
| Model | Gemini 3.5 Flash Lite (free tier), temperature 0 |
| Embeddings | `BAAI/bge-base-en-v1.5`, locally on CPU, cached on disk |
| Vector stores | Chroma on disk; Pinecone serverless (free Starter plan) |
| Tracing | OpenTelemetry, OpenInference, Arize Phoenix (local) |
| Tooling | uv, Python 3.12, pytest, GitHub Actions |

Everything runs on free tiers.

## Project structure

```
tax/
  pub17.py       # HTML -> data/sections.jsonl: 356 sections, heading paths, links
  index.py       # section and chunk nodes, embedding cache, Chroma and Pinecone, Search
  answer.py      # the model, the instructions, the citation check, refusals
  rag.py         # baseline: top 5, one model call
  agent.py       # the Workflow: start -> think -> act -> think ... -> answer
  golden.py      # golden set items and how a fact is matched
  tracing.py     # OpenTelemetry to Phoenix
evals/
  golden.json    # 80 questions: number, direct, colloquial, multi-hop, hard-hop, out of scope
  retrieval.py   # hit@k, MRR, multi-hop coverage, per index and store
  run.py         # every golden question through each system, scored, cached
  phoenix.py     # cached runs as Phoenix experiments
  results/       # the reports in this README
tests/           # parser, golden set, citation check, RAG and agent with a scripted model
```

## Getting started

```bash
uv sync
echo "GOOGLE_API_KEY=..." > .env              # a free key from Google AI Studio
uv run python -m tax.index                    # embeds the publication locally and builds Chroma
uv run python -m tax.agent "can I claim my mother as a dependent?"
uv run python -m tax.rag "..." [--chunks]     # the baseline
```

The eval and tracing:

```bash
uv run python -m evals.retrieval              # no model calls
uv run python -m evals.run                    # 80 questions x 3 systems, cached in storage/answers
uvx --from arize-phoenix phoenix serve        # in another terminal
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006 uv run python -m tax.agent "..."
uv run python -m evals.phoenix                # cached answers as experiments
```

Pinecone: add `PINECONE_API_KEY` to `.env`, then run `uv run python -m tax.index --pinecone` and `uv run python -m evals.retrieval --pinecone`.

To parse a new edition, save the HTML from https://www.irs.gov/publications/p17 as `data/p17.html` and run `uv run python -m tax.pub17`.

Tests need no key, index or model: `uv run pytest`.

| Variable | Default | |
|---|---|---|
| `GOOGLE_API_KEY` | none | Gemini, for answers |
| `PINECONE_API_KEY` | none | Only for the Pinecone store |
| `TAX_EMBED_MODEL` | `BAAI/bge-base-en-v1.5` | A local Hugging Face embedding model |
| `PHOENIX_COLLECTOR_ENDPOINT` | none | A Phoenix to send traces to |

## Not tax advice

The answers come from Pub 17 and cite it, but Pub 17 is general guidance and the model can still misread it. Check the cited sections before acting on an answer.
