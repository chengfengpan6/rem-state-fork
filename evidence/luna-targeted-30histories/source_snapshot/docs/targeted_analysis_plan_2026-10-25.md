# Prospective analysis of a targeted map-content diagnostic

Prepared 25 October 2026 before the new live execution. This plan concerns 30 newly selected formation histories, five Team conditions and two fixed conflict profiles per history. It is a prospective local analysis plan, not a claim of external preregistration or completed results. It does not revise the preserved 342-response or 219-response records.

## Question and scope

When actors can still inspect their complete formation record, does replacing an evidence-derived reliability map with a prespecified altered map change subsequent collective judgment on cases that directly challenge the altered context? The primary outcome asks whether the replacement changes conditional expected excess Brier loss. A separate descriptive measure asks whether forecasts move in the direction implied by the replacement. These are different questions: content responsiveness does not guarantee harm, and neither establishes a complete organizational-memory mechanism.

This is a targeted instrument diagnostic. Its units are eligible synthetic formation histories, not human teams, organizations, individual model responses, map cells or profile rows. The planned 30 histories are a fixed affordable sample, not a power-validated sample size or a guarantee of statistical significance. A statistically distinguishable contrast remains conditional on this task, eligibility rule, model access route and profile battery. No post hoc power calculation will be used to certify the study.

## Design fixed before responses

The formation task uses three rounds, one per context X/Y/Z, the existing IID .5 truth process and the fixed context-specific source-reliability matrix. Candidate integer seeds are considered in ascending order beginning at 20261027. The first 30 distinct eligible seeds are retained. Eligibility uses formation data only: the evidence-map estimate for B exceeds A in Y, the displayed altered map differs from the displayed evidence map, and the displayed Y-context map mean squared error against the generator increases strictly. Candidate decisions and exact checks must be preserved. Neither natural H readouts, model forecasts, future outcomes nor favorable effect signs enter selection. The target therefore is the distribution induced by this eligible-history generator; it is not the unconditional distribution of all task histories. Distinct generator seeds operationalize independent synthetic histories, but provider random streams and absence of temporal serving dependence cannot be attested.

P swaps the complete A and B cells of E in context Y, including estimate and uncertainty limits. All other cells remain fixed. P and E use the same display precision and neutral provenance. H is the map elicited during formation; R0 restores no external map at the fork; R0rep is a separately executed copy of that R0 state. R0 retains the ledger and can reconstruct reliability. H comparisons may additionally reflect provenance and elicitation differences.

Both fixed profiles have context Y. Their signals in A/B/C order are 100 and 011. Each profile starts from a fresh clone of the same post-formation fork for its condition. The profile branches do not receive one another's forecasts, messages, scores or feedback. No profile-to-profile learning, update trajectory or correction opportunity is studied. Each condition/profile uses the existing three-actor initial-forecast, message and revision sequence, with the three final probabilities averaged equally. The researcher-side true-DGP posterior is 21/242 for 100 and 221/242 for 011; neither is actor input. These profiles deliberately confront disagreeing A and B signals and are not sampled natural future rounds.

The planned successful-path count is 30 formation responses plus 5 conditions × 2 profiles × 9 responses = 120 responses per history, or 3,600 over 30 histories. Responses and attempts must be reported separately. Scheduling, transport, map delivery, no-writeback and completion are verified outside the statistical analysis. The analysis does not call a provider or treat a valid JSON file as proof of experimental integrity.

With one formation observation per context, eligibility fixes Y's A observation as incorrect and B as correct. Their E estimates are therefore 1/3 and 2/3 before display rounding; only C's correctness varies the Y estimate pattern. The 30 histories do not supply 30 arbitrary Y maps: there are two E/P point-estimate configurations in Y. Variation elsewhere in the record, actor behavior during formation and generated H remains possible. The inferential target must retain this restricted support.

## Primary estimand and single primary test

For history h, condition a and profile j, let p[h,a,j] be the mean final actor forecast. Let q[j] be the known true-DGP posterior. Recompute

```text
cBR[h,a,j] = (p[h,a,j] - q[j])^2
d[h] = ((cBR[h,P,100] - cBR[h,E,100])
      + (cBR[h,P,011] - cBR[h,E,011])) / 2
Delta = mean_h d[h]
```

The two profiles receive equal weight within each history, and histories receive equal weight in Delta. Positive Delta means higher expected excess Brier loss under P on this battery. The independent analysis sample has at most 30 observations, not 60 profiles, 150 conditions or 3,600 responses. cBR is conditional expected excess Brier loss relative to the true-DGP posterior, not a realized difference between two Brier scores after a sampled truth.

The sole primary inferential test is H0: E[d[h]] = 0 against a two-sided alternative at alpha .05. Calculate the one-sample t statistic on the history differences (equivalently a paired t test on history-mean P/E scores), with sample SD using n−1, standard error SD/sqrt(n), n−1 degrees of freedom, and a two-sided 95% t confidence interval. Report the estimate, SD, SE, interval, t statistic, degrees of freedom, p value and actual number of paired histories together. A positive estimate with two-sided p below .05 supports the prespecified direction in this selected setting; a negative estimate of that kind supports the opposite direction. A nonsignificant result is not equivalence or proof of absence.

The t interval is exact under independent normal history differences and an approximation otherwise. Histories from a pseudorandom generator with fixed exogenous selection support a model-based repeated-history interpretation; they are not a probability sample of organizations. Model drift, common backend shocks or dependence across executions can invalidate the independence approximation. Randomized/interleaved schedules help but do not prove it. No sign-flip/randomization p value is reported: arbitrary exchangeability of P and E or symmetry of the difference distribution is not established merely by pairing conditions.

## Prespecified sensitivity and descriptive summaries

Always report the median, minimum, maximum, quartiles, positive/negative/exact-zero counts and all 30 history differences. Exact zero means numerical equality in the stored/recomputed result, without an outcome-dependent tolerance. Display rounding must not determine the sign count. No observations are trimmed, winsorized or removed as outliers.

As a sensitivity analysis, compute a two-sided 95% percentile bootstrap interval for the primary mean from 10,000 resamples of complete history differences, with replacement, each of size n. Use NumPy PCG64 through `default_rng(20261025)` and linear 2.5th/97.5th percentiles. Profiles and actor rows are never resampled independently. This interval is a prespecified approximation with its own small-sample/skewness limitations, not a second primary test or a preferred result selected after seeing which interval excludes zero. Report it alongside the t interval and explicitly flag disagreement about inclusion of zero. If all differences coincide, label both the sample variance and bootstrap distribution degenerate; do not output a spurious finite t statistic or interpret zero estimated variance as perfect population precision. With fewer than two complete paired histories, do not calculate inferential quantities.

Report leave-one-history-out means as an influence description (their range and the history yielding the minimum/maximum), without deleting influential histories or running a replacement test. These summaries make sensitivity visible; they do not guarantee robust inference.

## Secondary contrasts and multiplicity

The two prespecified exploratory secondary loss contrasts are H−E and H−R0, each defined by averaging the same two profile-level cBR differences within history. Apply the same two-sided history-level t calculation. Adjust these two p values together using Holm's sequential procedure at family alpha .05. Report unadjusted p values, Holm-adjusted p values, ordinary marginal 95% t intervals and their explicit non-simultaneous status. If a secondary test cannot be computed, retain it in the two-member family with p=1 for adjustment bookkeeping and report its actual p value as unavailable. Do not promote a favorable secondary contrast into the primary claim.

The primary test is its own prespecified family. The exploratory secondary family has separate adjustment and is not a claim that all statements across the entire report have joint 95% coverage. There are no formal tests for profile-specific effects, H error, reversals, map endorsement, direction alignment, A/A variation, provider versions or causal mediation in this plan.

## A/A repeatability and direction diagnostic

For R0rep−R0, calculate the same history-mean cBR difference and describe its mean, sample SD, median, mean absolute difference, root mean square difference and extrema. Also report profile-level and history-averaged absolute forecast differences. The SD of history-averaged A/A differences estimates repeat discrepancy under this design and schedule; it combines response variation, order effects and any provider drift. It is not a pure internal-noise parameter. Dividing it by sqrt(2) would require additional equal-variance and independence assumptions and is not done. Do not test zero and call a nonsignificant result equivalence, or call the observed maximum a population noise ceiling. Compare P−E with A/A descriptively without subtracting noise from the primary estimate or imposing an invented success threshold.

For each history/profile, mechanically compute the conditional Bayesian forecast using the displayed E point estimates as source reliabilities and then using displayed P estimates, with the fixed .5 prior and conditional-independence rule. These are plug-in predictions under each supplied map, not truth or inferred model beliefs. Define g[h,j] as the sign of ideal_P−ideal_E and

```text
aligned_shift[h] = mean_j g[h,j] * (p[h,P,j] - p[h,E,j])
```

A positive value means movement in the direction implied by the assigned map replacement. Preserve both the signed ideal change and actual change, plus profile-specific values, so complementary profiles do not cancel artificially. Report its history mean, median, SD and sign counts without a p value or a separate success declaration. If an ideal difference is exactly zero, record zero alignment weight and flag the zero-direction profile. This diagnostic does not show that the model used Bayes' rule, endorsed the map or failed to read the ledger.

## Missing histories, failures and analysis freeze

All 30 selected history IDs remain in the report regardless of outcome or execution failure. A failed or incomplete history is not replaced by another seed. No outcome-based rerun, early stopping for significance, sample-size extension or removal of adverse contrasts is allowed. Operational recovery may consume a recorded successful prefix and finish the originally assigned requests under the already specified runtime policy, but its full attempt accounting and provenance must remain visible. A changed model, protocol or unprespecified retry is a separately labelled execution, not a silent continuation.

Each contrast requires both profiles and both relevant conditions within a history. It may use all its complete pairs even if another condition failed; actual contrast-specific n and missing IDs must be shown. Only complete paired histories enter its t/bootstrap calculation. Such estimates are conditional on completion and cannot establish the all-30 estimand if missingness depends on treatment or outcome. No probabilities, scores or means are imputed.

For each contrast, also give conservative bounds for the mean over all 30 selected histories: each unobserved history contrast can lie in [−1,1], because cBR lies in [0,1]. If m of N=30 histories have a complete contrast with sum S, the bounds are [(S−(N−m))/N, (S+(N−m))/N]. These are worst-case logical bounds, not confidence intervals. They deliberately do not turn partly observed histories into complete units. A partial-run report must be marked interim and nonfinal; p values are withheld until the execution has reached a terminal state, preventing a stream of inferential looks from becoming an undeclared stopping rule.

The plan, configuration, selected seed list, analysis code, dependency versions and source commit are frozen before live outcome inspection. The final analysis records input hashes and the exact code version. Amendments are dated and justified separately; the original plan remains recoverable. Tests use scripted fixtures only and establish arithmetic and data-validation behavior, not scientific significance, power or model validity.

## Interpretation boundaries and sources

This study addresses a bounded P−E content-sensitivity question. It cannot establish the historical representative-versus-misleading crossover hypothesis, post-update correction or persistence, an architecture interaction, a human-team mechanism, or recovery of latent w/lambda parameters. H−E is a natural-map comparison in the selected histories, not a test that the formation process generally produces inherited distortion. The earlier trajectory proposal's pre-update and full-horizon windows are not reproduced by these two independent no-update profiles.

The organizational motivation and construct boundaries are documented in `scenario_and_identification.md`, particularly March (1991), *Organization Science*, DOI [10.1287/orsc.2.1.71](https://doi.org/10.1287/orsc.2.1.71), and Brandon and Hollingshead (2004), *Organization Science*, DOI [10.1287/orsc.1040.0069](https://doi.org/10.1287/orsc.1040.0069). Their theories do not prescribe this statistical test, N=30 or these profiles. They are not cited as proof of task validity.

The statistical implementation follows the paired-difference logic described in the [NIST/SEMATECH e-Handbook paired-comparison section](https://www.itl.nist.gov/div898/handbook/eda/section3/eda353.htm), the formula, degrees of freedom and two-sided interval in [SciPy's official one-sample t documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_1samp.html), and the with-replacement resampling definition in [SciPy's official bootstrap documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html). Those public reference pages were checked on 25 October 2026; the local dependency lock, rather than the current website's release number, governs execution. These are authoritative statistical/software references, not purported FT50 organizational findings. The history-level aggregation, two-member Holm family, percentile sensitivity procedure, missing-data bounds and interpretation limits are declared project analysis choices. No source is represented as guaranteeing their finite-sample adequacy in this artificial system.
