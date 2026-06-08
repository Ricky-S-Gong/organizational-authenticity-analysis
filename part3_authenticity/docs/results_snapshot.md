# Part 3 Results Snapshot

This file is generated from the Part 3 summary outputs.

## Distribution

| metric | target_company_years | scored_company_years | missing_company_years | mean | median | std | min | p10 | p25 | p75 | p90 | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| authenticity_index | 450 | 328 | 122 | 41.977573 | 44.826058 | 17.544878 | 0.0 | 15.536537 | 30.81313 | 55.144853 | 62.38855 | 82.116295 |

## Sector Summary

| sector | target_company_years | scored_company_years | missing_company_years | mean | median | min | max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Consumer Discretionary | 90 | 59 | 31 | 36.314588 | 41.985019 | 0.513699 | 64.494591 |
| Energy | 90 | 62 | 28 | 47.026333 | 46.02937 | 1.565996 | 82.116295 |
| Financials | 90 | 74 | 16 | 37.078649 | 37.582795 | 0.598802 | 72.495791 |
| Healthcare | 90 | 73 | 17 | 46.736668 | 49.974606 | 6.26703 | 72.75885 |
| Technology | 90 | 60 | 30 | 42.580898 | 45.16014 | 0.0 | 66.093233 |

## Year Summary

| year | target_company_years | scored_company_years | missing_company_years | mean | median | min | max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2016 | 50 | 24 | 26 | 39.678974 | 41.995379 | 0.685871 | 69.556707 |
| 2017 | 50 | 31 | 19 | 37.59453 | 44.916254 | 0.237812 | 72.495791 |
| 2018 | 50 | 31 | 19 | 38.703584 | 39.093484 | 1.592719 | 71.69163 |
| 2019 | 50 | 36 | 14 | 42.086325 | 41.333575 | 0.513699 | 73.487773 |
| 2020 | 50 | 39 | 11 | 42.962756 | 46.270396 | 9.021407 | 82.116295 |
| 2021 | 50 | 41 | 9 | 43.267305 | 46.117647 | 0.0 | 74.876355 |
| 2022 | 50 | 40 | 10 | 43.202714 | 47.249172 | 9.312234 | 74.89405 |
| 2023 | 50 | 42 | 8 | 43.844109 | 47.252337 | 8.315098 | 73.351973 |
| 2024 | 50 | 44 | 6 | 43.566616 | 45.962155 | 6.26703 | 81.277728 |

## Sensitivity Summary

| comparison_metric | company_years | pearson_correlation | spearman_correlation |
| --- | --- | --- | --- |
| cosine_alignment | 328 | 0.918894 | 0.905912 |
| l1_alignment | 328 | 1.0 | 1.0 |
| jaccard_theme_overlap | 328 | 0.777823 | 0.756922 |
| semantic_text_similarity | 328 | 0.136493 | 0.121644 |
| part2_word_count | 328 | -0.04625 | 0.045907 |

## Keyword, Semantic, and Hybrid Summary

| metric | company_years | mean | median | std | min | p25 | p75 | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| keyword | 328 | 41.977573 | 44.826058 | 17.544878 | 0.0 | 30.81313 | 55.144853 | 82.116295 |
| semantic | 328 | 58.451335 | 57.830893 | 6.762498 | 42.421938 | 53.30875 | 62.358725 | 81.902372 |
| hybrid | 328 | 50.214454 | 51.167718 | 9.822718 | 21.51037 | 43.491475 | 57.437504 | 74.54622 |

## Keyword, Semantic, and Hybrid by Sector

| sector | keyword | semantic | hybrid |
| --- | --- | --- | --- |
| Consumer Discretionary | 36.314588 | 56.648531 | 46.481559 |
| Energy | 47.026333 | 60.231512 | 53.628922 |
| Financials | 37.078649 | 62.29653 | 49.687589 |
| Healthcare | 46.736668 | 55.90324 | 51.319954 |
| Technology | 42.580898 | 56.742355 | 49.661626 |

## Keyword, Semantic, and Hybrid by Year

| year | keyword | semantic | hybrid |
| --- | --- | --- | --- |
| 2016 | 39.678974 | 58.603616 | 49.141295 |
| 2017 | 37.59453 | 58.416984 | 48.005757 |
| 2018 | 38.703584 | 57.787061 | 48.245323 |
| 2019 | 42.086325 | 57.45008 | 49.768203 |
| 2020 | 42.962756 | 57.855626 | 50.409191 |
| 2021 | 43.267305 | 56.990307 | 50.128806 |
| 2022 | 43.202714 | 58.787187 | 50.99495 |
| 2023 | 43.844109 | 60.310437 | 52.077273 |
| 2024 | 43.566616 | 59.489208 | 51.527912 |

## Keyword-Semantic Quadrant Summary

| quadrant | company_years | mean_keyword | mean_semantic | mean_hybrid |
| --- | --- | --- | --- | --- |
| both_high | 98 | 55.548141 | 64.075263 | 59.811702 |
| both_low | 98 | 28.699026 | 52.487222 | 40.593124 |
| keyword_high_only | 66 | 56.794758 | 53.928658 | 55.361708 |
| semantic_high_only | 66 | 26.726779 | 63.479137 | 45.102958 |

## Keyword-Semantic Quadrant Representative Cases

| quadrant | ticker | company_name | sector | year | keyword | semantic | hybrid | keyword_minus_semantic |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| both_high | VLO | Valero Energy | Energy | 2024 | 81.277728 | 67.814712 | 74.54622 | 13.463015 |
| both_low | GS | Goldman Sachs | Financials | 2017 | 0.598802 | 42.421938 | 21.51037 | -41.823136 |
| keyword_high_only | ABBV | AbbVie | Healthcare | 2020 | 72.75885 | 50.957715 | 61.858282 | 21.801135 |
| semantic_high_only | GS | Goldman Sachs | Financials | 2020 | 9.021407 | 70.762902 | 39.892155 | -61.741496 |
