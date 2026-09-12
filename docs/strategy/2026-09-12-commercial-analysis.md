# Product forms and commercial evidence

Research checked 2026-09-12. Published prices below are USD, without currency
conversion; Faber offer hypotheses are EUR. Vendor case studies establish that an
adjacent category has customers, not that the customer wants Faber. Vendor-reported
metrics are not independently verified. No customer discovery call occurred.

## Evidence that affects the decision

| Primary evidence | What it establishes | What it does not establish |
|---|---|---|
| [Greptile pricing](https://www.greptile.com/pricing), checked September 12 | Pro lists $30/seat/month, 50 credits/seat, $1/additional credit; enterprise private deployment and security terms. An existing developer-tool budget and substantial price pressure. | Revenue for Faber, desire for an extra evidence product, or audited vendor effectiveness. |
| [Greptile customer stories](https://www.greptile.com/customers), checked September 12 | Publicly named users include Brex, Podium, Vouch, Gumloop, WorkOS and Browserbase. Teams already buy/use review assistance. | These are Faber leads, dissatisfied customers, or willing interviewees. |
| [Greptile TREX](https://www.greptile.com/trex), [learning](https://www.greptile.com/learning), [independence](https://www.greptile.com/independence), checked September 12 | Runtime-validation beta selects tests/tools from PR context, runs a sandbox and returns logs/screenshots/traces; other pages describe scoped rules, feedback learning and agent-independent review. Pricing meters TREX at three credits per review. Much closer overlap with A/B than a prose review bot. | Independently measured effectiveness, exact security architecture, or equivalence to owner-approved deterministic authority. Nonetheless runtime evidence and adaptation are not unique Faber claims. |
| [CodeRabbit pricing](https://www.coderabbit.ai/pricing), checked September 12 | Essentials $30 monthly/$24 annual per developer; Team $60/$48, with custom pre-merge checks. Enterprise includes self-hosting, identity and audit controls. | An unoccupied policy/governance market. Free public-repo reviews make OSS users harder to monetize. |
| [Qodo pricing](https://www.qodo.ai/pricing/), checked September 12 | Pro Team starts at $30 for 2,500 credits; page states $.012/credit, up to 30 users, rules and pre-PR skills; enterprise quoted. | Old $38-per-seat comparisons remain current. This is pooled usage, not a comparable seat price. |
| [Qodo rule system](https://www.qodo.ai/blog/introducing-qodo-rule-system/), February 17, 2026 | Already markets owned, versioned rules, discovery from history and accepted review feedback, lifecycle and enforcement. Direct competitive overlap with B. | That its model-based rule enforcement supplies Faber's deterministic execution guarantees. Product language alone cannot prove that distinction either. |
| [Anthropic Code Review launch](https://claude.com/blog/code-review), March 9, 2026 | Reports internal review overload, a Team/Enterprise review product and then-average $15–25 token-billed reviews. Names a TrueNAS example. High-value review can command more than commodity inference prices. | A current contracted price or causal quality/reviewer-time improvement. Launch claims must not be extrapolated to every team. |
| [CodeRabbit financing announcement](https://www.coderabbit.ai/newsroom/coderabbit-series-c-agentic-change-management), August 12, 2026 | Reports $143m Series C at $1.5bn and expansion into software change management. Strong investor activity, formidable funded competition. | Faber's addressable market, traction or fundraising case. Funding is not customer willingness to pay Faber. |
| [GitHub required-status semantics](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks), checked September 12 | Success, skipped and neutral can satisfy required status checks. Merge eligibility and exercised coverage differ. GitHub already binds checks to commit contexts and supports expected apps. | That skipping a particular check is wrong; owner policy decides applicability. A small existing CI assertion can often close the gap. |
| [LangSmith pricing](https://www.langchain.com/pricing), checked September 12 | Plus $39/seat/month plus usage; evaluation, tracing, deployment, gateway and enterprise controls. Buyer budget for C-adjacent infrastructure exists. | Demand for Faber's routing, or a need for another observability stack. |
| [Braintrust pricing](https://www.braintrust.dev/pricing), checked September 12 | Pro $249/month with usage allowances and enterprise private deployment. Paid evaluation/quality infrastructure exists. | That portable acceptance receipts are a separate budget line. |
| [Develocity predictive selection](https://docs.develocity.ai/2026.2/using-develocity/predictive-test-selection/), [Netflix case](https://develocity.ai/customers/story/netflix/), checked September 12 | Learned check selection has an established enterprise product and named deployment. Verification learning can be economically relevant. | That Faber has a better selector, unique dataset or broader policy-authoring advantage. Public list price for this specific extension was not established. |
| [Moderne customer studies](https://moderne.ai/case-study), checked September 12 | Named modernization adopters include Squarespace, Choice Hotels, Interactions and MEDHOST. Migration/reliability has a concrete engineering-budget owner. | Independent verification of time-saved claims, demand for a standalone verifier, or access to these customers. |
| [Cass / Schneider Electric case](https://www.cassinfo.com/freight-resources/case-studies/schneiderelectric), undated page, historical multi-year deployment | Real freight-audit buyer, incumbent implementation, and supplier-reported 1–5% audit savings depending on mode/region. Existing contract/invoice normalization is substantial. | An open greenfield opportunity or a quick enterprise deployment. The same case describes long integration and coordination. |
| [Nubimed insurer billing](https://www.nubimed.com/software-contabilidad-facturacion/), page dated October 2023; [billing detail](https://www.nubimed.com/blog/software-para-medicos-facturacion-mutuas/), November 2024, both checked September 12 | Spanish clinic software already handles insurer-specific prices, invoicing and payment tracking. A local vertical has incumbents close to the proposed workflow. | That rejection/recovery exceptions are fully solved; also no evidence clinics will buy a second product. |
| [METR follow-up design note](https://metr.org/blog/2026-02-24-uplift-update/), February 24, 2026 | Explains limits of measuring changing developer productivity, including selection and measurement problems. | That its early-2025 slowdown is a September-2026 forecast. Faber must measure total work, not assume agent output is economic value. |

Current repository-level pain is covered by the pinned [Hermes](../research/2026-09-12-hermes-policy-study.md),
[Omarchy](../research/2026-09-12-omarchy-policy-study.md), and
[nixpkgs](../research/2026-09-12-nixpkgs-policy-study.md) studies. These contain
actual incident histories and current check-selection limits. They demonstrate
technical work to be done, not a commercial buying process.

The master-only Duckbill field note describes review overload but has low evidence
weight: it records a practitioner social post, without audited defect or review-hour
data. It is a possible small-team archetype, not demand validation. Its prior numerical
claims are not used to forecast this business.

## Candidate A — OSS Proof with a hosted or enterprise layer

**Buyer / user / job.** Engineering lead buys; maintainers and release engineers use
it to review whether an agent patch meets a specific behavioral obligation. The
timing driver is more agent-created changes and existing review spend. Alternatives
are strong-agent review, ordinary CI, GitHub rulesets, CodeRabbit/Qodo/Greptile and
handwritten regression tests. Include TREX runtime validation in any real vendor
comparison; do not compare Faber's execution against only a prose reviewer.

**Difference / adoption.** Closed execution capability, exact evidence bindings and
counterexamples are useful design choices. Core integrity is not yet independently
cleared. An individual can run the no-key demo; real adoption needs owner-approved
catalog, environment and regression harness. It can sit beside GitHub; network effects
are unnecessary. A clean standalone extraction is engineering work, not customer proof.

**Economics / distribution.** Hypothesis: 2–8 weeks to a €500–€2,000 assisted pilot
after a qualified lead exists; self-serve sales could be faster but are unproven.
Recurring hypothesis €100–€500/repo/month or support/private-deployment contracts.
Likely sale: weeks for a team, months for enterprise. Distribute via reproducible
public examples and agent/CI integrations, without competing on free OSS review.
Market breadth is large but saturated.

**Moats / fatal risks / falsifier.** Technical moat is modest; open primitives can be
copied. Rights-cleared outcomes could improve scenario selection, but no proprietary
learning loop exists. Fatal risks are setup burden, weak coverage and incumbent bundling.
Cheapest test: ask one unfamiliar maintainer to use a real task without help, then
offer paid onboarding; stop productization if the free baseline is adequate.

## Candidate B — Repository-owned policy authoring and evolution

**Buyer / user / job.** CTO or platform/quality lead buys; senior reviewers maintain
the accepted risk scenarios and decide whether evidence is complete. Urgency depends
on repetitive maintenance/release checks consuming real review time. More coding
agents increase throughput pressure, but public upstreams already have rich policy.
Alternatives include Qodo rules, Greptile's runtime/learning products, code-review
instructions, CI scripts, CODEOWNERS, GitHub required workflows, Develocity for
predictive test selection, and strong-agent repo reading.

**Difference / adoption.** Generic generation and history mining are already offered.
The narrower possible value is carrying an incident into an owner-approved executable
scenario, preserving applicability and environment fidelity, and exposing incomplete
evidence. One team can adopt via a normal policy/test PR; no new record system or
cross-company network needed. Integration is repository docs, test harness and existing
CI outputs; hidden branch protection and intended semantics require owner input.

**Economics / distribution.** Hypothesis: €250 diagnostic or €1,000 pilot, 1–4 weeks
to first payment from a reachable qualified small team; no warm lead means longer.
Recurring €250–€750/repo/month for maintained checks only after repeat value. Sales
cycle days–weeks for discretionary services, 2–6 months for organization governance.
Distribution is specific incident writeups, referrals and direct founder conversations.
Breadth is substantial; initial task-family focus must be narrow.

**Moats / fatal risks / falsifier.** Technical moat low; accepted scenario libraries
and customer-specific workflow fit may accumulate switching value. A data moat requires
repeated comparable failures and permission, not scraped PR volume. Fatal risk: a
one-off agent-authored script solves it. Compare against that script over ten changes;
stop recurring product if upkeep equals savings or no buyer pays. **Best test now.**

## Candidate C — Verification-guided use of heterogeneous agents

**Buyer / user / job.** AI/platform lead buys; automation engineer uses routing and
escalation to obtain accepted work per total euro, including review. Why now: mixed
model capacities, local hardware and increasing agent workloads. Alternatives are
default frontier agents, simple retry/escalation, provider routing, LangSmith/Braintrust
and internal eval infrastructure.

**Difference / adoption.** Independent acceptance labels might make cheaper attempts
economical. That advantage is unmeasured and depends on a strong verifier first.
One organization can adopt; integrations include worker invocations, budgets, model
policies, cost capture and isolated execution. No network effect required, but moving
private code between providers adds procurement and policy constraints.

**Economics / distribution.** Hypothesis: 1–3 months to a €2,000–€10,000 optimization
study from an accessible team; enterprise sale 3–9 months. Recurring managed routing
or deployment/support revenue follows measured savings, not tokens routed. Distribution
via agent platform integrators and published reproducible economics. Breadth could be
large if verifiable task families generalize.

**Moats / fatal risks / falsifier.** A rights-cleared task/cost/accepted-outcome corpus
could create a learning moat; public benchmark wins and local GPU ownership do not.
Technical moat is moderate only with reliable verifiers and integration reliability.
Fatal risks: verifier/retry/human costs exceed savings, strong-model prices fall, or
false acceptance rises. Test 20 paired tasks after B supplies acceptance, versus both
frontier-first and simple cheap-first escalation. No routing product first.

## Candidate D — Agent-to-agent contracting and acceptance

**Buyer / user / job.** A firm procuring automated work or an agent-platform operator
would buy; buyer/provider agents and human operators use it. The painful job would be
defining deliverables, authority and dispute evidence across organizations. Emerging
agent protocols make this timely, but they do not establish a budget for Faber.
The [A2A specification](https://a2a-protocol.org/latest/specification/) already provides
task/artifact interaction primitives; contracts and acceptance remain application work.

**Difference / adoption.** Portable acceptance could complement transports and
payments, but Faber has no demonstrated inter-firm transaction. Adoption requires both
parties, identity, delegated authority, integration, dispute and operational agreements.
Unilateral adoption only works if narrowed back to a buyer-side tool. New shared records
and trust increase organizational friction; market liquidity may be required later.

**Economics / distribution.** Speculative €5,000–€25,000 design partnership in
3–9+ months; no validated pricing or sales cycle. Recurring API/enterprise or transaction
fees need actual transaction volume. Distribution through platforms is indirect and
slow. Market breadth is theoretically high, near-term demand uncertain.

**Moats / fatal risks / falsifier.** No technical or network moat yet. Repeated
accepted cross-party work could create reputation data, subject to gaming and rights.
Fatal risks: protocol commoditization, lack of demand and coordination overhead. Cheapest
test is one genuine buyer/provider transaction with existing tools; kill if Faber adds
no value beyond a task brief and human acceptance. Defer payments and marketplaces.

## Candidate E — A vertical reconciliation business

**Buyer / user / job.** Freight: shipper logistics finance/controller buys, audit staff
resolve invoice/accessorial exceptions. Spain: clinic owner/billing manager buys,
administrators reconcile insurer invoices and payments. Money is tied to concrete
transactions, independent of agent-code hype. Alternatives are Cass/other freight audit
services, TMS/accounting automation, clinic systems such as Nubimed, insurer portals
and outsourced billing.

**Difference / adoption.** Evidence provenance and explicit acceptance may support the
workflow, but existing code lacks domain extraction, contracts and connectors. Buyer-side
post-hoc exception review can be unilateral; shared insurer/carrier acceptance cannot.
CSV/document exports reduce integration only if lawful access and consistent rules
exist. Do not assume a clinic-insurer network is available.

**Economics / distribution.** Hypothesis: €1,000–€5,000 bounded manual audit in
2–8 weeks **with** a warm operator and usable exports, otherwise months; recurring fee
or per-case pricing requires recoverable value and low bespoke work. Enterprise freight
cycles can be multi-quarter; small clinic sales shorter but smaller budgets. Local
operator referrals could work; founder access is unknown. Both markets are broad,
but each subworkflow must be selected independently.

**Moats / fatal risks / falsifier.** Domain rules, integrations and operational feedback
would matter more than current Faber code. Proprietary case history needs rights;
customer documents do not grant training permission. Fatal risks: incumbent coverage,
contract-specific service labor, inaccessible evidence and regulated data burden.
Cheapest test: a billing operator walks through ten sanitized past exceptions and states
what their current system misses; obtain a paid diagnostic before any connector.
For clinic work, retain prior administrative-only scope; no care or coverage decisions.

## Candidate F — OSS/research with indirect value

**Buyer / user / job.** No software buyer required; maintainers/researchers use an
inspectable verifier and failure corpus. Sponsors, research partners or integrators
might later fund support/licensing. Alternatives include CI, existing evaluation
libraries and publishing the ideas without a framework. Why now: agent acceptance is
an active research and engineering issue.

**Difference / adoption.** Auditable negative findings, no-key replay and explicit
authority limits can be credible research contributions. One person can reproduce
locally; source/package integration is optional. No new system or network effects.
External validity, not schema breadth, is the needed contribution.

**Economics / distribution.** First direct paid engagement might take 1–6+ months
or never happen; €500–€5,000 sponsorship/support is an unvalidated offer range, not a
forecast. Recurring grants, support or licensing require separate agreement. Distribution
is a small reusable artifact, paper, incident study or integration. Audience breadth
moderate; buyer urgency weak. Reputation may help employment/partnerships but is not ARR.

**Moats / fatal risks / falsifier.** Open knowledge and reproducibility are distribution
assets; no automatic data or technical moat. Fatal risk is endless internal refinement
without external reuse. Cheapest test: three independent users reproduce a useful
result and at least one reuses a component. If not, archive rather than expanding scope.

## Candidate G — Verification for a specific migration or upgrade

**Buyer / user / job.** Engineering director or team lead buys; service owners need
confidence that a defined upgrade preserved compatibility. Existing migration budgets
and deadlines are stronger than abstract governance demand. Alternatives include
OpenRewrite/Moderne, migration consultants, comprehensive integration tests and strong
coding agents. This is an outcome service adjacent to B, not a generic refactoring tool.

**Difference / adoption.** A portable acceptance package could expose missing scenarios
and bind the exact deployed artifact/environment. The transformer often already owns
verification, so standalone value must be shown. One team can adopt without a market;
needs fixtures, support matrix, old/new behavior and staging evidence, not a new system
of record. Bespoke domain contracts are the main integration burden.

**Economics / distribution.** Hypothesis: €1,000–€5,000 acceptance package within
2–6 weeks for a scheduled small-team upgrade; 2–6+ months for enterprise. Recurring
revenue requires a continuing upgrade queue or repeatable scenario maintenance, rather
than one migration. Distribute through engineering consultancies and concrete examples.
Market breadth broad; choose one framework or service family first.

**Moats / fatal risks / falsifier.** Tested compatibility scenarios and domain experience
could compound; no current exclusive data advantage. Fatal risk is ordinary integration
testing already solves the whole job or each upgrade is bespoke. First ask a team with
an approved upgrade budget to pay for acceptance work. Prefer this task family inside
B when available; do not build migration generation infrastructure.

## Prospective customer archetypes, not a contact list

| Wedge | Observable qualifying archetype | Public examples and limits |
|---|---|---|
| B / A | Agent-heavy B2B product team with review tooling and repeated operational boundaries | Gumloop and Browserbase appear in Greptile's customer stories; WorkOS illustrates identity/API-sensitive engineering. These establish category fit only, with no claimed unmet demand or budget access. Prefer smaller reachable teams of this shape over chasing named logos. |
| G | Commercial software operator with a funded modernization queue | Squarespace, Choice Hotels and Interactions are named Moderne adopters. They demonstrate the budget class, but likely have mature tools and procurement; integration partners or smaller analogues are better initial targets. |
| E | Shipper/controller with expensive invoice exceptions, or clinic billing owner with unreconciled insurer payments | Schneider Electric validates freight-audit economics and warns of enterprise complexity. No clinic is named as a prospect because no public case here establishes unmet need. Nubimed is an incumbent/possible future integration partner, not a buyer. |

No personal contacts were scraped, messages sent, contracts invented, or revenue
claimed. The distinction is decisive: **there is real adjacent spending; there is
still no direct willingness-to-pay evidence for Faber's proposed increment.**
