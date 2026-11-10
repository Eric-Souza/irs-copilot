# Golden set: 80 questions, gemini-3.5-flash-lite

| System | Fact right | Fact, number | Fact, direct | Fact, colloquial | Fact, multi-hop | Fact, hard-hop | Cites a labeled section | Citations dropped | Refuses out of scope | Refuses in scope | Model calls | Tool calls | Tokens | Median latency |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rag-chunks | 75% | 74% | 82% | 85% | 77% | 33% | 43% | 0 | 91% | 16% | 1.00 | 0.00 | 3,012 | 0.9 s |
| rag-sections | 84% | 89% | 100% | 85% | 85% | 33% | 91% | 1 | 100% | 9% | 1.00 | 0.00 | 2,196 | 0.9 s |
| agent | 91% | 95% | 100% | 90% | 92% | 67% | 94% | 0 | 100% | 4% | 1.21 | 0.21 | 3,491 | 1.6 s |

Means per question, except latency. A fact is right when the answer contains it, ignoring case and spaces.

## Every wrong answer

### rag-chunks: 18

- **n03** (refused) What is the 2025 standard deduction for a single filer?  
  Expected ['10.10', '10.2'], found True, cited []  
  > I couldn't find this in IRS Publication 17 (2025).
- **n04** (refused) What is the standard deduction for married filing jointly in 2025?  
  Expected ['10.10', '10.7'], found True, cited []  
  > I couldn't find this in IRS Publication 17 (2025).
- **n05** (refused) What is the standard deduction for head of household?  
  Expected ['10.10'], found True, cited []  
  > I couldn't find this in IRS Publication 17 (2025).
- **n09** (refused) What is the maximum child tax credit per qualifying child?  
  Expected ['14.4'], found True, cited []  
  > I couldn't find this in IRS Publication 17 (2025).
- **n18** (refused) What is the maximum deduction for qualified tips in 2025?  
  Expected ['8.19'], found False, cited []  
  > I couldn't find this in IRS Publication 17 (2025).
- **d01** (no "3 years") How long should I keep the records that support my tax return?  
  Expected ['1.49'], found True, cited ['1.47']  
  > Generally, you must keep records that support items shown on your return until the period of limitations for that return runs out [1.47].
- **d02** (refused) What is the 2025 modified AGI limit for a single filer to contribute to a Roth IRA?  
  Expected ['9.38'], found False, cited []  
  > I couldn't find this in IRS Publication 17 (2025).
- **c06** (refused) My company gave me a watch for 10 years of service. Do I pay tax on it?  
  Expected ['5.3'], found True, cited []  
  > I couldn't find this in IRS Publication 17 (2025).
- **c13** (no "under age 24") My 23-year-old daughter is a full-time college student and lives with us. Can she still be my qualifying child?  
  Expected ['3.9'], found True, cited ['3.2']  
  > Yes, your 23-year-old daughter can still be your qualifying child if she is a student, is younger than you (or your spouse if filing jointly), and meets the other tests to be a qualifying child [3.2].
- **c16** (refused) I got a 1099-G for unemployment last year. Do I really have to pay tax on that?  
  Expected ['8.17'], found False, cited []  
  > I couldn't find this in IRS Publication 17 (2025).
- **m02** (refused) How much is the child tax credit, and at what income does it start to be reduced for married couples filing jointly?  
  Expected ['14.4', '14.10'], found False, cited []  
  > I couldn't find this in IRS Publication 17 (2025).
- **m09** (no "credit against your tax") I had to pay back income I reported in a prior year. Can I deduct it, or is there another option?  
  Expected ['12.19', '12.60'], found False, cited ['8.15']  
  > If the amount you repaid was more than $3,000, you can deduct the repayment as an other itemized deduction on Schedule A (Form 1040), line 16, if you included the income under a claim of right [8.15]. However, you can choose to take a credit for the year of repayment instead [8.15]. You should figur
- **m13** (no "15,750") I'm preparing the final return for my single father, who died in 2025 at age 60. What standard deduction do I use?  
  Expected ['10.2', '10.10'], found True, cited ['10.1']  
  > The standard deduction for a decedent's final tax return is the same as it would have been had the decedent continued to live, but if the decedent wasn't 65 or older at the time of death, the higher standard deduction for age can't be claimed [10.1].
- **h02** (no "$500") My child's SSN wasn't issued before the due date of my return. Can I still get any credit for this child?  
  Expected ['14.6', '14.7'], found True, cited ['14.5', '14.2']  
  > If your qualifying child does not have the required SSN (one that is valid for employment and issued by the SSA before the due date of your 2025 return, including extensions), you can't use the child to claim the Child Tax Credit (CTC) or Additional Child Tax Credit (ACTC) on either your original or
- **h03** (refused) What counts as gross income when deciding whether my aunt can be my qualifying relative, and what is the limit?  
  Expected ['3.14', '3.17'], found True, cited []  
  > I couldn't find this in IRS Publication 17 (2025).
- **h06** (no "substantial gainful activity") My disabled brother earns money at a sheltered workshop. Does that count toward the gross income test, and what counts as permanently and totally disabled?  
  Expected ['3.17', '3.9'], found True, cited ['3.16', '3.17']  
  > For purposes of the gross income test, the gross income of an individual who is permanently and totally disabled at any time during the year doesn't include income for services the individual performs at a sheltered workshop [3.16]. The availability of medical care at the workshop must be the main r
- **h07** (refused) My bank forgave part of my credit card debt and sent me a 1099-C. Is there any way I don't owe tax on it?  
  Expected ['8.3', '8.4'], found True, cited []  
  > I couldn't find this in IRS Publication 17 (2025).
- **o11** (answered) How much can I deduct for charitable donations to my church?  
  Expected [], found None, cited ['3.11']  
  > For more information about the deduction for charitable contributions, see Pub. 526 [3.11]. The provided text does not contain the specific rules or limits for deducting charitable donations to a church, as it refers readers to Pub. 526 [3.11].

### rag-sections: 11

- **n06** (refused) What is the standard deduction for a single person who is 65 or older?  
  Expected ['10.10', '10.3'], found True, cited []  
  > I couldn't find this in IRS Publication 17 (2025).
- **n19** (refused) How large is the bonus deduction for people age 65 or older?  
  Expected ['4.12'], found False, cited []  
  > I couldn't find this in IRS Publication 17 (2025).
- **c06** (refused) My company gave me a watch for 10 years of service. Do I pay tax on it?  
  Expected ['5.3'], found False, cited []  
  > I couldn't find this in IRS Publication 17 (2025).
- **c15** (refused) my siblings and I pay for our mom's living expenses together, who gets to claim her as a dependent?  
  Expected ['3.21'], found False, cited []  
  > I couldn't find this in IRS Publication 17 (2025).
- **c17** (no "part of your pay") I wait tables. Do I have to report my tips if they're cash?  
  Expected ['4.15'], found True, cited ['4.15']  
  > You must include your tips on your tax return on the same line as your regular pay. [4.15]
- **m01** (refused) Can my mother be my qualifying relative, and how much income can she have in 2025?  
  Expected ['3.14', '3.17'], found False, cited []  
  > I couldn't find this in IRS Publication 17 (2025).
- **m10** (no "February 15") I don't expect to owe any income tax this year. Can I have my employer stop withholding, and how long does that last?  
  Expected ['4.3', '4.12'], found True, cited ['4.12']  
  > You can claim exemption from withholding for 2026 only if both of the following situations apply: for 2025, you had a right to a refund of all federal income tax withheld because you had no tax liability, and for 2026, you expect a refund of all federal income tax withheld because you expect to have
- **h02** (no "$500") My child's SSN wasn't issued before the due date of my return. Can I still get any credit for this child?  
  Expected ['14.6', '14.7'], found True, cited ['14.6', '14.2']  
  > If your child doesn't have the required SSN issued before the due date of your 2025 return (including extensions), you can't use the child to claim the Child Tax Credit (CTC) or Additional Child Tax Credit (ACTC) on either your original or amended 2025 tax return [14.6]. However, if your qualifying 
- **h03** (refused) What counts as gross income when deciding whether my aunt can be my qualifying relative, and what is the limit?  
  Expected ['3.14', '3.17'], found True, cited []  
  > I couldn't find this in IRS Publication 17 (2025).
- **h06** (no "substantial gainful activity") My disabled brother earns money at a sheltered workshop. Does that count toward the gross income test, and what counts as permanently and totally disabled?  
  Expected ['3.17', '3.9'], found True, cited ['3.17']  
  > For purposes of the gross income test, the gross income of an individual who is permanently and totally disabled at any time during the year doesn't include income for services the individual performs at a sheltered workshop [3.17]. The publication does not provide a definition for "permanently and 
- **h07** (no "insolvent") My bank forgave part of my credit card debt and sent me a 1099-C. Is there any way I don't owe tax on it?  
  Expected ['8.3', '8.4'], found True, cited ['8.3']  
  > Yes, you have no income from the canceled debt if it is intended as a gift to you [8.3]. The publication doesn't cover any other ways to avoid tax on it.

### agent: 6

- **n19** (refused) How large is the bonus deduction for people age 65 or older?  
  Expected ['4.12'], found False, cited [], tools: search_publication(higher standard deduction amount age 65 or older Table 10-2)  
  > I couldn't find this in IRS Publication 17 (2025).
- **c06** (refused) My company gave me a watch for 10 years of service. Do I pay tax on it?  
  Expected ['5.3'], found False, cited []  
  > I couldn't find this in IRS Publication 17 (2025).
- **c17** (no "part of your pay") I wait tables. Do I have to report my tips if they're cash?  
  Expected ['4.15'], found True, cited ['4.15']  
  > Yes, you must include your tips on your tax return on the same line as your regular pay [4.15].
- **m01** (refused) Can my mother be my qualifying relative, and how much income can she have in 2025?  
  Expected ['3.14', '3.17'], found False, cited []  
  > I couldn't find this in IRS Publication 17 (2025).
- **h02** (no "$500") My child's SSN wasn't issued before the due date of my return. Can I still get any credit for this child?  
  Expected ['14.6', '14.7'], found True, cited ['14.6', '14.2']  
  > If your qualifying child does not have the required SSN issued before the due date of your 2025 return (including extensions), you can't use the child to claim the Child Tax Credit (CTC) or Additional Child Tax Credit (ACTC) on either your original or amended 2025 tax return [14.6]. However, if your
- **h06** (no "substantial gainful activity") My disabled brother earns money at a sheltered workshop. Does that count toward the gross income test, and what counts as permanently and totally disabled?  
  Expected ['3.17', '3.9'], found True, cited ['3.17']  
  > To meet the gross income test for a qualifying relative, a person's gross income for the year must be less than $5,200 [3.17]. For the purposes of the gross income test, the gross income of an individual who is permanently and totally disabled at any time during the year does not include income for 
