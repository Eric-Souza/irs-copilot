# Golden set: 80 questions, gemini-3.5-flash-lite

| System | Fact right | Fact, number | Fact, direct | Fact, colloquial | Fact, multi-hop | Fact, hard-hop | Cites a labeled section | Citations dropped | Refuses out of scope | Refuses in scope | Model calls | Tool calls | Tokens | Median latency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| agent-links | 96% | 95% | 100% | 100% | 100% | 67% | 99% | 0 | 100% | 1% | 1.30 | 0.30 | 3,946 | 5.8 s |

Means per question, except latency. A fact is right when the answer contains it, ignoring case and spaces.

## Every wrong answer

### agent-links: 3

- **n19** (refused) How large is the bonus deduction for people age 65 or older?  
  Expected ['4.12'], found False, cited [], tools: search_publication(Standard Deduction Table age 65 or older additional amount)  
  > I couldn't find this in IRS Publication 17 (2025).
- **h02** (no "$500") My child's SSN wasn't issued before the due date of my return. Can I still get any credit for this child?  
  Expected ['14.6', '14.7'], found True, cited ['14.6', '14.2'], tools: read_section(14.7)  
  > If your qualifying child doesn't have the required SSN issued before the due date of your 2025 return (including extensions), you can't use the child to claim the Child Tax Credit (CTC) or Additional Child Tax Credit (ACTC) on either your original or amended 2025 tax return [14.6]. However, if your 
- **h06** (no "substantial gainful activity") My disabled brother earns money at a sheltered workshop. Does that count toward the gross income test, and what counts as permanently and totally disabled?  
  Expected ['3.17', '3.9'], found True, cited ['3.17']  
  > For the purposes of the gross income test, the gross income of an individual who is permanently and totally disabled at any time during the year does not include income for services the individual performs at a sheltered workshop, provided the availability of medical care at the workshop is the main
