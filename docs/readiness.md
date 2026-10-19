# Readiness and evidence boundaries

This repository is an executable research prototype. A small real-model smoke run, offline tests, recorded-response replay and a journal submission are different deliverables. Each should be claimed only when its corresponding evidence exists. The scientific protocol remains a prototype specification, not a preregistered confirmatory study.

## What the Organization Science call requires

The relevant journal is **Organization Science**, not *Operations Research*. Its [official call listing](https://pubsonline.informs.org/page/orsc/calls-for-papers) links the [seven-page special-issue CFP](https://pubsonline.informs.org/pb-assets/filesorsc/CFP_AI-Enabled%20Frontiers%20in%20Organizational%20Science-1785685920943.pdf). These sources were checked on 19 October 2026.

Stage 1 asks for a roughly 3–5 page, 1,500–2,000 word proposal plus references, a technical appendix or supplement, and a Git repository or equivalent artifact containing a prototype or proof of concept (PDF p.3). It does not specify GitHub as the sole host or explicitly require global public access at Stage 1. The artifact must nevertheless be accessible for assessment. Final publication calls for a public GitHub repository or an accessible equivalent research object (p.4).

A repository therefore helps supply the research artifact, but does not replace the proposal, scientific contribution or technical explanation. This appendix describes the implementation; a submission appendix must additionally connect the implemented evidence, planned development, key risks and claimed contribution.

The general [submission guidelines](https://pubsonline.informs.org/page/orsc/submission-guidelines) specify double-blind review. The special-issue PDF does not state an exemption or a special repository-anonymization procedure. A public repository for technical review and the eventual review package can be prepared separately; follow the actual submission instructions rather than assuming a named repository is automatically suitable for anonymous review.

The CFP specifies no named software license. Sharing should cover code and data the authors can legitimately distribute, with third-party material identified. It allows a differently focused longer paper elsewhere subject to copyright and duplicate-publication boundaries (p.6). The [transparency policy](https://pubsonline.informs.org/page/orsc/data-and-methods-transparency) additionally emphasizes accurate disclosure of research sequence, changes and AI use.

## Dates and selection status

The Stage-1 portal opened on 1 October 2026 and closes on Sunday 1 November 2026. The checked materials did not establish a precise deadline time or timezone. Selection notification is scheduled by 10 January 2027; development runs January–May 2027. The PDF tentatively specifies 27–28 February for the workshop, while the [companion site](https://orgsci.org/) states February without exact days. At least one author's attendance is expected, with exceptions considered. Finalization is planned for summer and the target issue for autumn 2027 (PDF pp.4–5).

Stage 1 is the main selection gate, but passing it is not an unconditional publication guarantee: editorial removal remains possible in exceptional circumstances, and the final format depends on development. The companion site names auditability as a criterion where the PDF names development stage; both favor an inspectable research artifact. No change to the repository requirements or November deadline was found in the checked official sources.

## What each level of evidence establishes

| Evidence | Supported claim | Claim it does not support |
|---|---|---|
| Scripted-provider/offline tests | Particular code paths satisfy tested properties | A real model followed the protocol or exhibited a scientific effect |
| Successful real-model responses | The requested transport returned observed responses for specified tasks | Every configured branch completed, or the server model identity was independently verified |
| Completed smoke manifest plus raw trace | The named short configuration ran to completion and is inspectable | Population generalization, mechanism identification, parameter recovery or adequate power |
| State and future-tape checks | Implemented copies and respondent input boundaries satisfy the checked invariants | Perfect provider-level independence, equal effective context, or equivalence to human organizational memory |
| Exact recorded-response replay | Archived responses reproduce the substantive engine outputs | A fresh live rerun will give identical responses or is universally accessible |
| Clean-install reproduction | The documented environment can rebuild the checked offline results | All external model access and account requirements have disappeared |
| A public repository | Reviewers and readers can inspect the released materials | Completion of the Stage-1 proposal, scientific novelty or editorial acceptance |

The status of a run must be read from its committed manifest and summary, not inferred from the presence of this documentation. Check attempted versus expected calls, completed branches, terminal status, errors and the requested model. Failed or partial runs remain valid engineering evidence when labeled accurately; they must not be relabeled as completed studies. Repository documentation should point to the specific release artifacts that substantiate any completion statement.

## Required release checks

Before calling a release reproducible, check the following against that release's exact commit and configuration:

1. Installation and offline tests work in a clean environment using the documented dependencies.
2. Requests are paired with their responses and failures; records preserve the task inputs, schema, model request and available transport metadata without exposing credentials.
3. Future truths, true reliability parameters, branch labels and researcher metrics are absent from respondent inputs. Copies do not share mutable state across branches.
4. Audit/probe readouts leave live state unchanged, and checkpoint ordering matches the declared lifecycle.
5. Exact recorded-response replay consumes the intended trace and reproduces substantive outputs. Timestamps and replay transport metadata may legitimately differ.
6. Public files contain original/shareable code and synthetic-task research traces. Private correspondence, manuscript attachments, recordings, credentials and unrelated projects are excluded.
7. A live run is reported with its actual transport and access requirements. If the adapter uses a subscription-authenticated Codex route, it is described that way, without inventing a public API endpoint or implying unlimited calls.

These are engineering release criteria, not extra requirements attributed to the CFP. They do not independently validate the theoretical interpretation.

## Scientific work remaining beyond a smoke

The short configuration observes only a few rounds and a single sampled history. Its final map update is not followed by further forecasts. It cannot show sustained persistence, correction, adaptation after repeated updates, or a reliable relation between history M and actual map distortion. Batched probes are diagnostic and do not validate recovery of separate source weights or forecast scale.

Before a larger study, the map lifecycle, substantive estimand, interval interpretation, comparison architecture and measurement procedure need calibration. Real-model pilot data are needed to assess protocol compliance, map use, probability granularity, output variation, failure rates and costs. Confirmatory sample sizes and stopping thresholds must follow that work. Results from an earlier scripted surrogate or a different truth-balancing generator cannot be substituted for this evidence.

The repository deliberately separates an inspectable tool from a substantive empirical claim. A failed or null smoke can reveal an implementation or measurement boundary; a successful smoke shows that a particular technical path works. Neither outcome alone establishes that retaining a shared reliability map improves or harms organizational decision making.
