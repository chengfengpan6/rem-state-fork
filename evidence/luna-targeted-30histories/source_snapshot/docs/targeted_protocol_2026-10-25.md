# Targeted map-content sensitivity diagnostic: prospective protocol

**Protocol:** `rem-prototype-0.2-targeted-Y-v1`  
**Frozen design date:** 25 October 2026  
**Model requested:** `gpt-5.6-luna`  
**Planned independent formation histories:** 30  
**Successful-path model requests:** 3,600  
**Status of this document:** prospective design; it does not report completed model runs or results.

## 1. Organizational question and bounded purpose

Can an inherited assessment of source reliability change a team's judgment when the complete evidence supporting that assessment remains available? The organizational object is a shared interpretation of experience: a table saying which information sources have been dependable in which situations. The intervention changes that interpretation while preserving the underlying record. It concerns the use of an inherited representation, rather than adding information that the team otherwise lacks.

Organizational-memory research distinguishes retained information from its subsequent interpretation and use; expertise research distinguishes recognizing expertise from using it in decisions. Those distinctions motivate separate records, a reliability representation, and forecasts. They do not establish that a synthetic table constitutes an entire transactive memory system, nor that language-model actors reproduce human organizational behavior. The current study targets one narrow prerequisite for the larger instrument: **behavioral sensitivity to experimentally changed map content** under a team workflow. Huber (1991), Walsh and Ungson (1991), Bunderson (2003), and Csaszar and Eggers (2013) motivate these distinctions; none prescribes the numerical task or sample size below.

The primary comparison is a deliberately distorted evidence-based map, P, against its undistorted counterpart, E. Both use the same display format and have access to the same records. Naturally formed H is retained as a secondary condition. R0 and an independently requested R0 replicate anchor the absence of a supplied table and response repeatability. This design does not identify a uniquely social mechanism: every arm uses the same interactive team architecture.

## 2. Relationship to earlier protocols

This is a new, fixed-profile diagnostic rather than an extension of a previous run's future tape. Earlier engineering checks used one history, a short continuation, multiple architectures, and an update path. Their unchanged records remain separate. In particular, a prior single future event occurred in X while the displayed P/E difference occurred in Y; that run did not directly test forecast sensitivity in the manipulated context.

This protocol therefore tests two prespecified conflicting-signal profiles in **Y**, the manipulated context. P swaps only Y's A/B cells; X and Z are unchanged. A full-horizon candidate with 24 formation rounds, 84 continuation rounds, and an update every 12 rounds remains a separate future design. The present fixed-fork test has no update window, no correction trajectory, and no test of the earlier H1–H4 crossover hypotheses. It also does not estimate the surrogate parameters w or lambda.

The five-arm content contrast, matched display precision, stage-specific map instructions, replicate branch, source hashes, and interleaving follow the instrument's design review. Three-round formation, two complementary Y profiles, the eligibility rule, N=30, and the resulting 3,600-request budget are new implementation and sampling choices. They are not a reproduction of an earlier suggested 12+6-round diagnostic and are not derived from a power analysis.

## 3. Formation task and recorded state

There are three information sources, A, B, and C, and three analyst actors, also labeled A, B, and C. A source is a noisy signal channel; an actor is a model invocation with an information role. The two must not be interpreted as the same psychological entity. Initially each actor receives its associated source's current signal; all labeled signals are disclosed before communication and final revision.

The researcher-side stationary reliability matrix is:

| Context | Source A | Source B | Source C |
|---|---:|---:|---:|
| X | .85 | .65 | .50 |
| Y | .50 | .85 | .65 |
| Z | .65 | .50 | .85 |

Truth is drawn independently as Bernoulli(.5). Source signals are conditionally independent given truth and context. The three formation rounds contain one shuffled occurrence of each context. This uses the implemented IID-truth generator, rather than the older manuscript's exact truth quotas. Actors know the .5 independent truth process and that source reliability is unknown and context-dependent; the true matrix and researcher oracles are never supplied to them.

Every formation round has nine calls: three private initial forecasts, three simultaneous messages after signal disclosure, and three revised forecasts after the messages are available. Messages are limited to 600 characters. No actor sees another actor's same-stage unfinished output. A team's forecast is the arithmetic mean of its three revised probabilities. Truth and scores are appended only after those forecasts are complete.

The checkpoint has four explicit slots: LE, the observed signal/truth ledger; LB, the recorded forecasts and scores; Pi, the actor's private decision record; and H, the persistent reliability table. The complete formation LE/LB and each actor's corresponding Pi survive the fork in every arm. No pre-fork discussion transcript is restored. Resetting H does not remove facts or erase those decision records.

After the three rounds, each actor independently supplies nine estimates and subjective 90% intervals from the same frozen checkpoint. Coordinatewise medians of the three readouts produce H0. This adds three calls, so one formation history costs **30** calls. This investigator-chosen aggregation creates a common research object; it is not a direct observation of spontaneous consensus. Original readouts and the pooled H0 must both be retained.

## 4. Prospective history selection

`tools/prepare_targeted_histories.py` examines integer seeds in ascending order, beginning at 20261027. These are RNG identifiers, not calendar dates. It stops at the first 30 eligible seeds, with a prespecified upper limit of 10,000 examined candidates. Previously used seeds are explicitly excluded; they are already below this lower bound. No eligibility condition can be relaxed after model results become available.

Eligibility uses only the three exogenous formation observations. E0 is calculated from those observations using independent Beta(1,1) priors for each context/source cell. Each E cell contains the posterior mean and the equal-tail 90% credible interval. P0 swaps the entire estimate/lower/upper values of Y:A and Y:B while retaining the destination labels. Both are rendered to two decimals before eligibility is checked.

The candidate qualifies only when:

1. The displayed E estimate for Y:B is strictly greater than that for Y:A.
2. The displayed Y maps differ between P and E.
3. P's mean squared point-estimate error across the three Y cells is strictly larger than E's, relative to the true Y reliabilities.
4. No cell outside Y changes.

All strict numerical checks use rational arithmetic on the displayed decimals, so a floating-point tie cannot become a positive manipulation. The eligibility calculation is a researcher-side manipulation check, not a behavioral outcome. It never uses H0, actor language, forecasts, future outcomes, or a desired observed treatment effect. The generator's unused continuation is not examined; the two testing profiles are fixed independently below.

**What this selection implies:** three formation rounds supply only one observation per context. An eligible Y event necessarily has A wrong and B correct. Thus E's displayed Y:A/Y:B point estimates are always .33/.67; P displays .67/.33. Y:C has only two possible estimates, .33 or .67. The 30 cases therefore are not 30 arbitrary Y maps. They vary in X/Z evidence, truth and signal realizations, context order, and subsequently generated model states. Their Y display has two point-estimate patterns determined by C. This deliberate conditional population improves stimulus clarity but cannot establish how common harmful natural H maps are.

The frozen selection examined **75 candidates**, yielding **30 qualifying seeds**. All 30 observable formation ledgers also have distinct hashes; this was recorded, not imposed as an additional outcome-dependent filter. Full candidate ledgers, rendered maps, exact checks, accepted/rejected statuses, selector hash, and DGP source hash are stored in `configs/targeted_30histories.json`. The same file defines the runner configuration. No model requests are made by the selection tool.

## 5. Five treatment arms

| Arm | Map at the fork | Meaning |
|---|---|---|
| P | E0 with the complete Y:A/Y:B values exchanged | Assigned source-attribution error in a matched table |
| E | Unmodified E0 from the shared formation ledger | Explicit evidence-based summary of the same available observations |
| H | Three-actor median H0 | Endogenously elicited team representation |
| R0 | `H: null` | No supplied persistent table; actors may still reconstruct one from records |
| R0rep | Independently requested duplicate of R0 | Within-history repeatability observation |

P and E must have identical schema, numerical precision, and neutral provenance wording. They must not disclose condition names, that an error was planted, true source reliabilities, or the oracle. H has a neutral factual line saying that the table was formed from the earlier team and shared with teammates; its natural provenance differs from E. H−E therefore bundles map content and that provenance distinction and is not a pure randomized manipulation of endogenous error magnitude.

The universal instruction to report all nine map cells is absent from forecast and message stages. It appears only when eliciting a map. There is no instruction to obey the supplied map, disregard contrary records, or make the expected contrast appear. Spontaneous reconstruction, explicit rejection, and numerical copying remain possible behaviors to record.

R0 is operationally “no supplied table,” not “no reliability representation anywhere.” The complete ledger can be summarized by the actor during forecasting or messaging. This makes P−E the cleanest current content intervention, while H−R0 remains a secondary, broader comparison of supplying a naturally formed summary.

## 6. Two fixed testing profiles and clone isolation

| Profile | Context | A | B | C | Researcher-only oracle Pr(truth=1) |
|---|---|---:|---:|---:|---:|
| Y100 | Y | 1 | 0 | 0 | 21/242 = .0867768595 |
| Y011 | Y | 0 | 1 | 1 | 221/242 = .9132231405 |

These profiles place A against B and C; the second is the bitwise complement of the first. With the true reliabilities and prior .5, Y100's likelihood for truth 1 is .5×.15×.35, and for truth 0 it is .5×.85×.65. Normalizing gives 21/242. Complementation gives the other oracle. These probabilities are used only by the researcher to score the final team forecast.

Both profiles start from a fresh deep clone of **the identical arm-specific fork checkpoint**. The first profile's messages, forecasts, scores, or inferred beliefs must not enter the second profile. Neither profile receives realized truth or feedback, and neither changes H. They are designed decision inputs, not two sampled continuation events with a realized outcome. Consequently the runner reports conditional Brier regret, not a fabricated realized Brier score.

Each profile repeats the same nine-call team process: three initial forecasts on private signals, three simultaneous messages after all signals are disclosed, and three revised forecasts after all messages are available. The two profiles therefore cost **18 calls per arm per history**. Initial and final forecasts and full messages are saved. There are no additional live belief audits, recall probes, or map-update calls in this diagnostic.

Under literal likelihood-based use of the displayed map, the P swap pushes Y100's forecast upward and Y011's forecast downward, away from their true oracles. For example, using unrounded Beta means, E's Y100 posterior is 1/3 or 1/9 depending on C, while P's is 8/9 or 2/3. The displayed two-decimal values slightly change these numbers. This is a mathematical benchmark, not a requirement imposed on actors or a guarantee of an observed effect. Agents may correctly resist the supplied error by recomputing from their records.

## 7. Outcomes, estimands, and statistical units

Let p(h,a,j) be the mean revised forecast of the three actors for history h, arm a, and profile j. With researcher oracle q(j), conditional Brier regret is:

```text
cBR(h,a,j) = [p(h,a,j) - q(j)]^2
C(h,a) = mean over the two fixed profiles of cBR(h,a,j)
D(h) = C(h,P) - C(h,E)
Primary estimate = mean over the 30 histories of D(h)
```

Subtracting the oracle's expected Brier score from a forecast's expected Brier score gives `(p-q)^2`. The oracle is a property of the specified DGP, not an inaccessible real-world truth claim. The two fixed profiles receive equal weight by design; this is not a natural-frequency average over all possible Y signals or all contexts.

The **history is the inferential unit**. The two profiles, five arms, three actor forecasts, and multiple stages are nested or paired observations, not additional independent histories. The primary analysis is a two-sided one-sample t test of the 30 paired history differences against zero, alpha=.05, with their mean, SD, SE, 95% t confidence interval, and every history difference reported. The fixed target is a conditional mean over eligible histories under this serving workflow. Approximate inference relies on independence across histories and the adequacy of a t approximation for their bounded differences; N=30 is a resource choice, not proof of adequate power or normality.

A 10,000-resample percentile bootstrap resamples complete histories, retaining all their paired conditions and profiles, with RNG seed 20261025. It is a sensitivity interval accompanying the t analysis; no choice between intervals is made based on significance. Standard references for the paired-difference and implementation mechanics are NIST's paired-sample discussion and SciPy's official `ttest_1samp` and `bootstrap` documentation. Those are methods references, not organizational-theory or FT50 evidence.

Two secondary mean contrasts, H−E and H−R0, use the same history-level aggregation and are adjusted together using Holm's procedure at family alpha=.05. They are secondary regardless of their p values. No confirmatory moderation analysis is assigned: the selected histories have a restricted Y pattern, and 30 cases cannot establish the previous natural-history crossover.

Report the following descriptively without promoting an additional primary test:

- Aligned content shift: `0.5 * [(pP,Y100-pE,Y100) - (pP,Y011-pE,Y011)]` per history. Positive values indicate movement in the planted-error direction. Behavioral movement and score deterioration are related but different outcomes.
- R0rep−R0: signed mean, SD, absolute differences, and the full paired distribution. Thirty repeat pairs provide more repeatability information than one pair, but do not identify a universal noise floor. A nonsignificant repeat contrast is not evidence of equivalence.
- Formation H0 estimates, interval widths, disagreement among the three original readouts, and cellwise distance from E and the true matrix. H0's relation to history is descriptive here; successful P−E does not establish the endogenous formation link.
- Individual and aggregate forecasts, initial-to-revised movement, and full messages as inspectable traces. Message language alone does not identify a psychological mediator.

## 8. Scheduling, traceability, and failures

Matched branches and profiles are interleaved or randomized using the frozen scheduling seed 20261027, independently of model outcomes. Two workers may run independent histories concurrently. Record actual request times, branch/profile order, and role/source-list order. Existing source-list and message-order permutation does not balance every JSON key or map-cell position; do not describe it as complete removal of position bias.

Each history's common formation checkpoint is constructed once and reused across arms. Within each arm, the two profile clones must have identical LE/LB/Pi and the prescribed H. A semantic verifier must compare delivered H against the arm's expected object, confirm unchanged X/Z in P, confirm no oracle/condition leakage, and confirm no profile-to-profile carryover. Hashes, raw prompts, responses, schema validation, requested model, transport, and source version are archived. A missing served model identity is recorded as missing, not replaced with the requested alias.

The expected budget is:

| Component | Per history | For 30 histories |
|---|---:|---:|
| Three formation rounds × nine calls | 27 | 810 |
| Three independent H0 readouts | 3 | 90 |
| Five arms × two profiles × nine calls | 90 | 2,700 |
| **Total** | **120** | **3,600** |

The executable safety limits are 32 formation calls per history, 20 calls per arm/history, and 3,660 cumulative physical dispatch reservations. The 60-request allowance above the successful path does not authorize automatic retry or discretionary extra cases. An invalid response or transport failure stops the affected execution for review; resume is explicit and must preserve all prior attempts and the frozen sample. No additional or replacement seed is selected, and no failed or unfavorable observation is silently replaced. A resume must recover completed calls rather than regenerate them and must count actual extra dispatches against the cumulative cap.

If a matched outcome is missing, report planned and completed histories for each contrast and the reason. The primary completed-pair analysis is conditional on completion. With cBR in [0,1], an unobserved history difference lies in [-1,1]; report corresponding worst-case mean bounds over all 30 planned histories when completion is incomplete. Partial traces remain engineering evidence but do not become complete experimental units. No stopping rule depends on statistical significance.

## 9. Interpretation and boundaries

A positive P−E mean with an uncertainty interval excluding zero would support sensitivity to the specified error-bearing table under this model, selected formation histories, profiles, record access, and team process. It would not demonstrate an organization-level general law, natural-H harm, persistence after correction opportunities, or a specifically social mechanism. A negative result would not be relabelled an implementation failure without independent delivery evidence. A result near zero remains compatible with resistance to the map, insufficient precision, or a weak response for this population; the interval and repeat distribution must accompany that interpretation.

The point of the planted contrast is to complement natural H. Natural formation can produce accurate, inaccurate, or weakly differentiated maps; if its mean effect is small, that alone does not tell whether the instrument can detect a meaningful content intervention. A deliberately changed table offers a known intervention while retaining an unforced response. The next scientific steps—if justified by these data—are independent formation validation, a longer correction trajectory, matched interaction controls, and explicit information-access boundaries. They require new protocols rather than retrospective reinterpretation of this targeted diagnostic.

## 10. References and source-reading scope

- Huber, G. P. (1991). Organizational Learning: The Contributing Processes and the Literatures. *Organization Science*, 2(1), 88–115. [DOI](https://doi.org/10.1287/orsc.2.1.88). Publisher abstract and opening text inspected; used for the process distinction.
- Walsh, J. P., & Ungson, G. R. (1991). Organizational Memory. *Academy of Management Review*, 16(1), 57–91. [DOI](https://doi.org/10.5465/amr.1991.4278992). Abstract and methodological passage inspected; not claimed as a full current methods review.
- Bunderson, J. S. (2003). Recognizing and Utilizing Expertise in Work Groups: A Status Characteristics Perspective. *Administrative Science Quarterly*, 48(4), 557–591. [DOI](https://doi.org/10.2307/3556637). Publisher abstract and author-university record inspected; used only for expertise recognition/utilization.
- Csaszar, F. A., & Eggers, J. P. (2013). Organizational Decision Making: An Information Aggregation View. *Management Science*, 59(10), 2257–2277. [DOI](https://doi.org/10.1287/mnsc.1120.1698). Author-hosted preprint sections 2–3, 4.3, and 5 inspected in the underlying design review; its continuous-evaluation model is not this binary task.
- Gneiting, T., & Raftery, A. E. (2007). Strictly Proper Scoring Rules, Prediction, and Estimation. *Journal of the American Statistical Association*, 102, 359–378. [DOI](https://doi.org/10.1198/016214506000001437). Relevant scoring-rule material inspected in the prior methods audit; the cBR identity here is also derived directly. The DOI endpoint did not provide fresh full text during this preparation.
- NIST/SEMATECH. [Two-Sample t-Test for Equal Means](https://www.itl.nist.gov/div898/handbook/eda/section3/eda353.htm). Current page inspected for its explicit paired-observation/difference distinction; its main displayed formula concerns unpaired data and is not substituted for the paired analysis here.
- SciPy. [`ttest_1samp`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_1samp.html) and [`bootstrap`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html). Official API documentation inspected by the analysis reviewer for the declared one-sample and paired-resampling implementation.

The selection, number of histories, two profiles, 600-character cap, three-read median, and scheduling policy are declared investigator choices. No cited source is presented as validating those exact values or guaranteeing an effect.
