# Take-Home Assessment: Deep Requirements Analysis

## 1. What This Assessment Is Actually Testing

This is not merely a scraping or NLP exercise. It is an end-to-end research engineering assessment that tests whether the candidate can turn an intentionally underspecified social-science question into a transparent, reproducible, scalable empirical study.

The evaluators explicitly name three capabilities:

1. **Technical skill:** collecting difficult historical web and document data, cleaning text, applying NLP/LLM methods, constructing datasets, and writing maintainable code.
2. **Analytical judgment:** making defensible choices where no single correct method exists.
3. **Handling incomplete instructions:** identifying ambiguity, making assumptions explicit, documenting tradeoffs, and avoiding false certainty.

The strongest submission will therefore optimize for **research credibility and transparency**, not just model sophistication or dataset size.

## 2. Global Hard Requirements

### Fixed sample

All four parts must use the supplied list of 50 companies:

- 10 Technology companies
- 10 Financials companies
- 10 Healthcare companies
- 10 Consumer Discretionary companies
- 10 Energy companies

The assignment describes these as the 10 largest companies by market capitalization in each sector, using the S&P 500 composition as of January 2024. The supplied company list should be treated as authoritative unless an inconsistency is discovered and documented.

### Primary time window

The target period is **2016–2024**.

- Part 1 explicitly requires one annual snapshot per company, producing 9 company-year observations per company and approximately 450 observations in total.
- Part 2 asks for as many years as feasibly available within the same window.
- Parts 3 and 4 should inherit the overlapping company-year coverage produced by Parts 1 and 2.

### Required deliverables for every part

Each part must include:

- Fully commented code in a structured repository
- A part-specific `README.md` explaining:
  - what was done
  - why it was done
  - assumptions
  - what would be done differently with more time
  - known limitations
- Output data files
- A written summary of no more than 1–2 pages that translates technical results into actionable, non-technical insights

These are not optional packaging details. They are part of the evaluation of reproducibility, communication, and judgment.

## 3. Cross-Part Research Logic

The four parts form a single research pipeline:

```text
Part 1: What companies say they value
                    +
Part 2: What company disclosures suggest they prioritize
                    ↓
Part 3: A transparent measure of alignment between the two
                    ↓
Part 4: A scientifically interesting analysis using the measure or source data
```

Decisions made early will constrain later parts. In particular:

- Part 1 and Part 2 need compatible thematic representations for Part 3.
- Company identifiers, years, sector labels, and provenance fields must be standardized across datasets.
- Missing-data rules must preserve the distinction between “not observed,” “not disclosed,” and “not mentioned.”
- Every transformation should retain enough provenance to audit how a final score was produced.

## 4. Part 1: Stated Values

### Explicit requirements

Use the Wayback Machine CDX API to collect archived versions of each company's corporate “About Us” page or an equivalent mission/values page.

Required target:

- 50 companies
- 2016–2024 inclusive
- One snapshot per company per year
- Approximately 450 snapshots

For every company, the submission must define and document:

- How the correct page was identified
- What counts as an equivalent mission/values page
- How page URL changes over time are handled
- How missing snapshots are handled
- How redirect chains are handled

For every collected snapshot:

- Extract visible body text
- Remove navigation, footer, and boilerplate
- Analyze whether the page changed from the prior year
- Identify value or thematic categories
- Identify notable linguistic shifts over time

The minimum required output schema is:

```text
ticker
company_name
sector
year
page_text_clean
changed_from_prior
theme_categories
analyst_notes
```

### Hidden methodological challenges

#### Page identity is a research decision

A company's “About Us” URL may change, redirect, split into multiple pages, or cease to exist. Selecting a URL only once and applying it to all years could create artificial missingness or compare different page types.

A defensible method needs a documented page-selection hierarchy and evidence for each company-year choice.

#### “One snapshot per year” is underspecified

The assignment does not define whether to select:

- the first available snapshot
- the last available snapshot
- the snapshot nearest a fixed annual date
- the highest-quality successful response

The selection rule must be consistent, justified, and deterministic. It should also account for repeated captures, non-HTML responses, soft 404s, and captures that merely redirect.

#### Page change is not a binary triviality

Raw HTML changes constantly because of timestamps, navigation, scripts, and layout. A useful `changed_from_prior` measure should operate on cleaned substantive text and distinguish minor edits from meaningful changes.

#### LLM outputs require reproducibility controls

An LLM-based pipeline should document:

- model and version
- prompt or prompt template
- inference parameters
- output schema
- retry and validation rules
- evidence supporting classifications
- estimated cost and scalability

The evaluator is likely to reward a simple, auditable pipeline over an elaborate but opaque one.

### What evaluators explicitly prioritize

- Scrape completeness
- Robust text extraction
- Thoughtful analytical categories
- Documentation and justification of every gap

Coverage does not need to be 100%. Undocumented gaps are worse than well-explained missing data.

### Part 1 completion criteria

Part 1 is complete when:

- All 450 target company-years have a status record, even when no usable page is found.
- Every usable record has source URL, capture timestamp, raw/clean provenance, and extraction status.
- Page-selection and missing-data rules are documented and reproducible.
- Text-change and thematic outputs can be audited.
- Coverage and failure modes are summarized.
- The required dataset, README, code, and 1–2 page summary exist.

## 5. Part 2: Lived Values

### Explicit requirements

Choose exactly one document type:

- ESG report
- sustainability report
- DEI report
- proxy statement

Collect that same document type for the same 50 companies across as many years as feasibly available from 2016–2024.

The candidate chooses the source, such as:

- company investor-relations pages
- SEC EDGAR
- third-party aggregators

The source and all coverage gaps must be documented.

Apply text mining to analyze:

- Within-company changes in language, tone, and topic emphasis over time
- Cross-company and cross-sector variation
- Shifts that appear to coincide with relevant external events

Any combination of classical NLP and LLM-assisted methods is allowed, but the methodological choices must be justified.

The output dataset schema is open-ended. Every column and the reason for including it must be documented.

### Central interpretation risk

The label “lived values” is stronger than the evidence requested. Corporate disclosures reveal what firms report, emphasize, and claim to prioritize; they do not directly observe behavior.

The submission should avoid treating disclosure language as definitive proof of actual behavior. This is a major construct-validity issue that should be carried into Part 3.

### Document-type tradeoffs

The selected document type determines coverage, comparability, and validity:

- **Proxy statements:** likely the most consistently available through SEC EDGAR, but their content is shaped by legal requirements and may only indirectly reflect organizational values.
- **Sustainability/ESG reports:** more directly relevant to stated priorities, but naming, availability, length, and reporting frameworks vary substantially.
- **DEI reports:** highly relevant to one value domain but likely sparse and inconsistent across companies and years.

The best choice is not necessarily the most conceptually appealing document. It should balance construct relevance, longitudinal coverage, cross-company comparability, and acquisition reliability.

### Hidden methodological challenges

- Reports may change titles or combine document types over time.
- PDF extraction quality can vary, especially for scanned or highly designed reports.
- Document length differences can dominate raw word counts.
- Regulatory templates and boilerplate can create misleading similarity.
- External-event analysis can easily become post hoc storytelling unless events and expected effects are defined transparently.
- Comparisons require normalization for document length and possibly document sections.

### Part 2 completion criteria

Part 2 is complete when:

- One document type has been selected and justified.
- Every company-year has a documented collection status.
- Original source, document URL, publication year, and extraction quality are retained.
- The schema and every column are documented.
- Methods support within-company, cross-company, and cross-sector comparisons.
- External-event claims are framed cautiously and supported by evidence.
- The required dataset, README, code, and 1–2 page summary exist.

## 6. Part 3: Organizational Authenticity Index

### Explicit requirements

Use outputs from Parts 1 and 2 to propose and implement a measure of organizational authenticity: the degree of alignment between what a company says it values and what its disclosures and behaviors suggest it prioritizes.

The measure must:

- Explicitly operationalize “alignment”
- Vary across companies
- Vary over time
- Include basic distributional analysis
- Include at least one validity check
- Acknowledge at least two limitations or threats to validity

There is no single correct measure. Coherence and transparency of reasoning are explicitly evaluated.

### Core design decision

The measure requires a shared representation of Parts 1 and 2. Possible interpretations include:

- overlap between theme-category distributions
- semantic similarity between statements and disclosures
- consistency between stated priorities and disclosure emphasis
- penalties for large gaps between highly stated and weakly disclosed themes

The chosen operationalization must explain what a high or low score means, what it does not mean, and why it represents authenticity rather than generic textual similarity.

### Major validity risks

- **Construct validity:** disclosures are not direct behavioral evidence.
- **Common-method bias:** both sides may be corporate communications.
- **Missingness bias:** companies with fewer accessible documents may receive distorted scores.
- **Document-length bias:** longer disclosures may appear more aligned simply because they mention more topics.
- **Sector bias:** sectors differ in expected terminology and reporting obligations.
- **Temporal mismatch:** publication dates and page snapshots may refer to different periods.
- **Model dependence:** LLM or embedding choices may materially alter scores.

### Validity-check expectations

The requested validity check is modest, but a credible submission should avoid circular validation. Examples include:

- manual review of selected high- and low-scoring cases
- sensitivity to alternative scoring specifications
- comparison against a separately sourced external indicator
- checking whether scores remain meaningful after controlling for document length or sector

### Part 3 completion criteria

Part 3 is complete when:

- The theoretical definition and mathematical implementation are explicit.
- Every score can be traced to source observations.
- The measure varies by company and year without being driven mainly by missingness or document length.
- Distributional properties are reported.
- At least one validity check and two limitations are documented.
- Sensitivity or robustness analysis demonstrates awareness of modeling dependence.
- The required dataset, README, code, and 1–2 page summary exist.

## 7. Part 4: Candidate-Proposed Analysis

### Explicit requirements

Propose one additional analysis using either:

- the organizational authenticity measure, or
- the underlying data

The analysis must be briefly implemented, even if only as a preliminary version, and its findings must be reported.

The evaluators explicitly prioritize:

- intellectual curiosity
- scientific reasoning
- a well-argued exploratory finding over a superficial confirmatory finding

### What makes a strong proposal

A strong Part 4 should:

- ask a clear question motivated by Parts 1–3
- specify the expected relationship or competing explanations
- use an analysis that is feasible with the available data
- distinguish exploratory evidence from causal claims
- discuss alternative interpretations
- add insight rather than merely re-plotting the authenticity index

### Part 4 completion criteria

Part 4 is complete when:

- The research question is clear and genuinely extends the earlier work.
- The method is proportionate to the available data.
- The preliminary analysis is reproducible.
- Findings are interpreted cautiously.
- Limitations and alternative explanations are stated.
- The required output, README, code, and 1–2 page summary exist.

## 8. Cross-Cutting Data and Engineering Requirements

### Reproducibility

The repository should make it possible to understand and rerun each stage without relying on undocumented manual steps.

At minimum, future implementation should retain:

- source URLs and timestamps
- retrieval status and error reason
- raw artifact identifiers or paths
- cleaned-text identifiers or paths
- transformation versions
- model and prompt metadata where LLMs are used
- deterministic company and year keys

### Scalability

Part 1 explicitly says the methods should be designed to scale. This does not require premature infrastructure, but it does require:

- deterministic rules
- resumable collection
- separation of raw data, processed data, and analysis outputs
- structured logs or status fields
- batchable model calls
- minimal manual intervention that is clearly recorded when unavoidable

### Human review

Because the data and constructs are noisy, human review should be treated as a validation layer rather than hidden cleanup. Any manual corrections should be recorded in an auditable manifest.

### Responsible interpretation

The final work should avoid:

- equating text similarity with genuine ethical authenticity
- presenting exploratory event coincidences as causal effects
- treating missing documents as absence of a value
- overstating precision from LLM classifications

## 9. Key Decisions to Resolve Before Part 1 Implementation

The following choices should be made explicitly when Part 1 begins:

1. The annual snapshot-selection rule.
2. The page-identification hierarchy and whether multiple historical URLs are allowed per company.
3. The exact definition of a successful capture.
4. Raw artifact retention policy, given Wayback Machine terms and repository size.
5. Boilerplate-removal method and quality checks.
6. Definition and threshold for `changed_from_prior`.
7. Theme taxonomy construction method.
8. LLM provider/model, structured output design, and reproducibility metadata.
9. Manual-review sampling strategy.
10. Whether large generated data files belong in Git, Git LFS, or an external data store.

## 10. Recommended Execution Order

1. **Establish shared schemas and provenance rules.**
   Verify by creating a small, auditable pilot for several companies and years.
2. **Complete Part 1 collection and analysis.**
   Verify coverage, extraction quality, category consistency, and documented gaps.
3. **Pilot candidate Part 2 document types before committing.**
   Verify longitudinal coverage and extraction quality across sectors.
4. **Complete Part 2 using the chosen document type.**
   Verify comparability and provenance.
5. **Design Part 3 only after inspecting both datasets.**
   Verify the index is interpretable, traceable, and not dominated by artifacts.
6. **Choose Part 4 based on patterns and limitations discovered earlier.**
   Verify that the analysis adds a meaningful scientific question.

## 11. Overall Submission Success Criteria

The complete submission should demonstrate:

- Every required company and target year has an explicit status.
- Data gaps and methodological choices are visible rather than hidden.
- Code, data, documentation, and summaries agree with one another.
- The research logic from stated values to lived-value disclosures to authenticity is coherent.
- Findings are understandable to a non-technical reader.
- Claims are proportionate to the evidence.
- The repository is organized, reproducible, and ready to scale beyond the pilot sample.

