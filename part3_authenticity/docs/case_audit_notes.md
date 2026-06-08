# Part 3 Case Audit Notes

This note provides a qualitative reading guide for selected high-alignment, low-alignment, and
keyword-semantic divergence cases. These cases are audit targets, not evidence of actual culture or
behavior.

## How Cases Were Selected

The audit starts from `outputs/validity_case_audit.csv`, which lists the 10 highest and 10 lowest
keyword-index company-years. I then add divergence cases from the keyword-vs-semantic comparison:

- **Keyword-high / semantic-lower cases:** high theme-distribution overlap but weaker whole-text
  semantic similarity.
- **Keyword-low / semantic-higher cases:** weak keyword theme overlap but stronger whole-text
  semantic relatedness.

This split is useful because the two measures answer different questions. The keyword index asks
whether the stated-values and proxy texts emphasize the same taxonomy themes in similar shares. The
semantic score asks whether representative text windows are broadly similar in embedding space.

## High-Alignment Cases

### Marathon Petroleum, 2020

Marathon Petroleum 2020 is the highest-scoring company-year in the panel, with a keyword
authenticity index of 82.12. The stated-values side emphasizes leadership and accountability,
shareholders and performance, and customers and service. The proxy side also heavily emphasizes
shareholders and performance, employees and workplace, and leadership and accountability. This is a
face-valid high-alignment case because the stated-values language and proxy disclosure language
share several major themes rather than merely one incidental keyword.

The semantic score is more moderate after rescaling, which suggests that the two documents align in
theme distribution more strongly than in whole-text rhetoric. That distinction is plausible because
a short corporate About page and a long proxy statement can share values themes while still having
different document genres and sentence-level language.

### Valero Energy, 2024

Valero 2024 also has very high keyword alignment at 81.28. The stated-values side is led by
environment and sustainability, leadership and accountability, and customers and service. The proxy
side is led by environment and sustainability, leadership and accountability, and employees and
workplace. This is a strong case for the intended interpretation of the index: official disclosure
priorities visibly mirror several of the themes that appear in the company's public values language.

The case should still be interpreted as disclosure alignment rather than behavioral proof. A high
score does not demonstrate environmental or workplace performance; it shows that the company's two
public communication channels are thematically consistent.

### AbbVie, 2020

AbbVie 2020 scores 72.76 on the keyword index. The stated-values side emphasizes customers and
service, health/safety/wellbeing, and employees/workplace, while the proxy side emphasizes
employees/workplace, leadership/accountability, and customers/service. This is substantively
intuitive because a healthcare company might plausibly connect public values language about
patients, health, and employees with proxy disclosure language about human capital and governance.

Its semantic score is relatively low compared with its keyword score, which makes it a useful
reminder that theme overlap and whole-text similarity are not identical. The theme categories line
up, but the broader language of the two artifacts may still differ.

## Low-Alignment Cases

### NVIDIA, 2021

NVIDIA 2021 has a keyword authenticity index of 0.00. The stated-values evidence is concentrated
in purpose and identity, while the proxy disclosure is led by DEI, employees/workplace, and
leadership/accountability. In the keyword framework, this is a clean low-alignment case: the public
values page and the proxy statement emphasize different parts of the taxonomy.

This is not evidence that NVIDIA is inauthentic. It is evidence that the specific stated-values
artifact captured for that year is thematically narrow relative to the proxy statement.

### Microsoft, 2017

Microsoft 2017 scores 0.24. Like NVIDIA 2021, the stated-values side is concentrated in purpose and
identity, while the proxy disclosure is led by shareholders/performance, employees/workplace, and
leadership/accountability. The result illustrates one common low-score mechanism: a short or highly
brand-oriented stated-values page can produce a narrow theme distribution that does not overlap
much with a governance-oriented proxy statement.

### Target, 2019

Target 2019 scores 0.51. Its stated-values evidence is concentrated in innovation and excellence,
while its proxy disclosure is led by shareholders/performance, leadership/accountability, and DEI.
This is an audit signal that the page-level values language and the proxy-disclosure priorities are
not describing the organization through the same thematic lens.

## Keyword-Semantic Quadrant Cases

The keyword-vs-semantic scatter plot uses the median keyword score and median rescaled semantic
score to divide the 328 scored company-years into four groups:

- Both high: 98 company-years.
- Both low: 98 company-years.
- Keyword high only: 66 company-years.
- Semantic high only: 66 company-years.

### Both High: Valero Energy, 2024

Valero 2024 is both keyword-high and semantic-high. It has very high keyword alignment because
environment/sustainability and leadership/accountability appear prominently on both sides. It also
has high semantic similarity on the rescaled embedding measure, suggesting that the representative
text windows are broadly related beyond shared taxonomy labels. This is the cleanest kind of
public-artifact consistency case: both the auditable theme distribution and the whole-text
embedding comparison point in the same direction.

### Both Low: Goldman Sachs, 2017

Goldman Sachs 2017 is both keyword-low and semantic-low. Its stated-values evidence is concentrated
in innovation/excellence, while its proxy disclosure is dominated by shareholders/performance,
leadership/accountability, and DEI. The semantic score is also low after rescaling. This is a
strong audit target because the two artifacts diverge both in taxonomy-theme emphasis and in
whole-text semantic relatedness. It still should not be read as proof of actual inauthenticity;
it is a signal that the captured stated-values artifact and proxy statement are not aligned.

### Keyword High Only: AbbVie, 2020

AbbVie 2020 has high keyword alignment but lower semantic similarity. The stated-values page and
proxy disclosure share important taxonomy themes, including customers/service, employees/workplace,
leadership/accountability, and health-related language. However, the whole-text embedding score is
closer to the middle of the semantic distribution. This pattern is plausible when a short values
page and a long proxy statement use different rhetorical styles while still emphasizing similar
themes. It supports keeping the keyword index as the primary auditable measure.

### Semantic High Only: Goldman Sachs, 2020

Goldman Sachs 2020 has high semantic similarity but low keyword alignment. The two representative
text windows appear broadly similar in embedding space, likely because they share financial-sector,
governance, and corporate language. But the values-theme distribution does not overlap much: the
stated-values side is narrow, while the proxy side is heavily weighted toward
shareholders/performance, leadership/accountability, and DEI. This is a good human-review case
because it may reveal either sector-level boilerplate similarity or taxonomy blind spots, but it
does not overturn the low keyword-index result.

## Audit Takeaway

The case audit supports keeping the keyword index as the primary score and semantic similarity as a
supplement. Both-high and both-low cases are easiest to interpret because the two measures agree.
Keyword-high-only and semantic-high-only cases are more diagnostically interesting because they
show where theme-distribution alignment and broad semantic relatedness diverge. The next research
step would be section-level proxy parsing or theme-level semantic comparison, which fits naturally
as a Part 4 extension.
