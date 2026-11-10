# IRS Copilot: plan

An agent that answers questions about the 2025 U.S. federal income tax return from IRS Publication 17 (2025), Your Federal Income Tax. Every answer cites the publication's sections. The agent follows Pub 17's own cross-references when one section isn't enough, and says so when Pub 17 doesn't cover the question. It is the U.S. counterpart of irpf-copilot: it reuses that project's agent, eval, stores and tracing, with a new parser and a new golden set.

## Stack (free)

| Part | Choice |
|---|---|
| Corpus | Pub 17 (2025), HTML edition from irs.gov, parsed into 356 sections |
| Framework | LlamaIndex 0.14: `VectorStoreIndex`, Workflows |
| LLM | Gemini 3.5 Flash Lite (free tier) through `llama-index-llms-google-genai` |
| Embeddings | `BAAI/bge-base-en-v1.5`, locally on CPU, cached on disk |
| Vector store | Chroma on disk locally; Pinecone serverless (free Starter plan) hosted, with the same embeddings in both |
| Tracing | Phoenix, locally, through `openinference-instrumentation-llama-index` |
| Tooling | uv, Python 3.12, pytest, GitHub Actions |

## Corpus

irs.gov publishes Pub 17 as a PDF and as one HTML page. The HTML is the better source:

- Headings carry their level in a class (`role-hd1` to `role-hd3`), so each section gets its heading path without guessing from font sizes.
- Each "see *Qualifying Relative*, later" and "see chapter 3" is a link to an anchor, so a section's cross-references are exact. Irpf-copilot had to parse "Consulte a pergunta 353" from the text.

`tax/pub17.py` keeps chapters 1 to 14 and drops the additional material after them. It turns every heading into a section numbered by chapter (3.9 is chapter 3's ninth section), with the text under it, and the sections its links point to. A link to a chapter goes to the chapter's first section. A section is the unit cited and retrieved, and long sections (the median is 1,036 characters, the longest 29,312) are split under their heading. The baseline is fixed-size chunks over the running text with no headings.

Two parser fixes came from the eval rather than from reading the HTML:

- A chapter's anchor sits just before its title, inside the previous chapter's last section. So links to chapter 3 were first credited to chapter 2's last section.
- The 2025 Standard Deduction Tables have a figure title, not a section heading, so they landed at the end of "Who Should Itemize". The chunk holding the tables then carried the wrong heading and didn't rank, and both RAG systems answered "What is the standard deduction for a single filer?" with a refusal. They are now section 10.10.

## Golden set

80 questions in `evals/golden.json`:

| Kind | Count |
|---|---|
| numbers and dates | 19 |
| close to Pub 17's wording | 11 |
| colloquial | 20 |
| multi-hop | 13 |
| hard-hop | 6 |
| out of scope | 11 |

Each item is labeled with the sections that answer it and a fact the answer must contain. Tests check that:

- each fact is in a labeled section's text
- for multi-hop and hard-hop items, the fact is in the hop section and not in the first one
- the hop section is reachable from the first one within two links

Hard-hop items are the multi-hop pairs where retrieval brings the first section but not the hop. They are picked by running retrieval, so after any change to the parser or the index they have to be checked again. Splitting out the standard deduction tables put the old h01's hop in the top 5, so h01 became the multi-hop m13, and h07 replaced it.

The out-of-scope questions cover topics Pub 17 now sends to other publications (capital gains, the mortgage interest and medical deductions, charitable contributions, the earned income credit), state taxes, other years and other countries.

## Metrics

- **Retrieval:** hit@k and MRR on the labeled sections, multi-hop coverage, and context size.
- **Answers:**
  - the fact is stated
  - the answer cites a labeled section and nothing it didn't read
  - it refuses out-of-scope questions and doesn't refuse in-scope ones
- **Cost:** model calls, tool calls, tokens and latency.

Every run is traced to Phoenix and logged there as an experiment on the golden set.

## Milestones

1. **Parse** (done): 356 sections in 14 chapters. 140 sections have links, 285 links in all.
2. **Golden set** (done): 80 questions, with tests against the parsed text.
3. **Index and baseline RAG** (done): 557 section nodes and 354 chunks, in Chroma and Pinecone. Retrieval, top 5 on the 69 answerable questions:

   | Index | hit@1 | hit@5 | MRR@10 | Multi-hop, both @5 | Hard-hop, second @5 | Context at 5 |
   |---|---|---|---|---|---|---|
   | sections | 74% | 94% | 0.83 | 92% | 0% | 7,150 chars |
   | chunks | 64% | 91% | 0.75 | 77% | 50% | 10,949 chars |

   Pinecone gives the same scores at about 200 ms a query, against 3 ms for Chroma.
4. **Agent and answer eval** (done). The first run used up the Gemini free tier's daily quota after 211 of 237 answers, and the rest ran the next day from the cache. On the 80 questions:

   | System | Fact right | Multi-hop | Hard-hop | Refuses out of scope | Refuses in scope | Model calls | Tokens |
   |---|---|---|---|---|---|---|---|
   | RAG over chunks | 75% | 77% | 33% (2/6) | 91% | 16% | 1.00 | 3,012 |
   | RAG over sections | 84% | 85% | 33% (2/6) | 100% | 9% | 1.00 | 2,196 |
   | Agent over sections | 91% | 92% | 67% (4/6) | 100% | 4% | 1.21 | 3,491 |

   Unlike irpf-copilot, the agent gains 7 points over RAG on sections. Its 15 tool calls were all `search_publication`, never `read_section`: a reworded search found the hop section each time it mattered, and on the two hard-hop misses (h02, h06) it made no tool call. Nudging it to follow links is the obvious next experiment.
5. **Phoenix experiments, README, CI** (done): the three cached runs are logged in Phoenix as experiments on the `irs-golden` dataset, the README has the results, and CI runs the 129 tests. Medium article and LinkedIn project still to do.
