# Retrieval: BAAI/bge-base-en-v1.5 in pinecone, top 10

80 golden questions, 69 with an answer in the publication.

| Index | hit@1 | hit@5 | MRR@10 | hit@5 number | hit@5 direct | hit@5 colloquial | hit@5 multi-hop | hit@5 hard-hop | Multi-hop, second section @5 | Both @5 | Hard-hop, second section @5 | Context at 5 (chars) | Median query |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sections | 74% | 94% | 0.83 | 95% | 100% | 90% | 92% | 100% | 92% | 92% | 0% | 7,230 | 215 ms |
| chunks | 64% | 91% | 0.75 | 95% | 91% | 90% | 85% | 100% | 77% | 77% | 50% | 10,949 | 293 ms |

Median similarity of the top result: sections: 0.754 in scope, 0.655 out of scope; chunks: 0.726 in scope, 0.637 out of scope.

## Misses at 5

| Question | Kind | Expected | sections rank | chunks rank |
|---|---|---|---|---|
| n18: What is the maximum deduction for qualified tips in 2025? | number | 8.19 | 2 | 9 |
| n19: How large is the bonus deduction for people age 65 or older? | number | 4.12 | - | 5 |
| d02: What is the 2025 modified AGI limit for a single filer to contribute to a Roth IRA? | direct | 9.38 | 3 | 6 |
| c06: My company gave me a watch for 10 years of service. Do I pay tax on it? | colloquial | 5.3 | - | 1 |
| c09: I'm legally blind. Do I get a bigger standard deduction? | colloquial | 10.4 | 1 | 10 |
| c15: my siblings and I pay for our mom's living expenses together, who gets to claim her as a dependent? | colloquial | 3.21 | 10 | 2 |
| c16: I got a 1099-G for unemployment last year. Do I really have to pay tax on that? | colloquial | 8.17 | 1 | 6 |
| m01: Can my mother be my qualifying relative, and how much income can she have in 2025? | multi-hop | 3.14, 3.17 | 8 | 2 |
| m02: How much is the child tax credit, and at what income does it start to be reduced for married couples filing jointly? | multi-hop | 14.4, 14.10 | 1 | - |
| m09: I had to pay back income I reported in a prior year. Can I deduct it, or is there another option? | multi-hop | 12.19, 12.60 | 1 | 8 |
