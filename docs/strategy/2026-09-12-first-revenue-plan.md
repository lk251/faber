# First-revenue offer and delivery plan

Proposed on 2026-09-12. No customer has received this offer and no payment has been
made. Prices are hypotheses to test, expressed in EUR before applicable taxes.

## The offer a buyer can evaluate

**Acceptance evidence pilot — €1,000, two weeks.** For one repository and one repeated
maintenance or upgrade family, identify what reviewers need to accept a change,
show where current evidence is incomplete, and leave up to two reusable checks or
policy improvements in the team's existing workflow.

The buyer is a founder/CTO or engineering lead who already spends meaningful time
reviewing agent-assisted changes. The default scope is dependency upgrades in one
Python backend service, preserving its existing API/CLI behavior. Confirm a real
upgrade queue and usable checks before accepting the pilot; do not bundle unrelated
configuration, security and migration work. This family is a delivery hypothesis,
not a finding that the public upstream studies demonstrated a Python-upgrade market.
Authentication redesign, production incident response and security certification
are outside the first engagement.

| Offer term | Concrete scope |
|---|---|
| Input | One repo or lawful redacted export; ten historical changes including known regressions where available; current CI/policy; one named owner. |
| Deliverable 1 | A short acceptance matrix: risk classes, existing checks, mandatory scenarios, skipped/unknown coverage, environment identity and human boundaries. |
| Deliverable 2 | Up to two owner-reviewed regression/check or evidence-capture improvements, delivered as an ordinary patch for customer review. |
| Deliverable 3 | Before/after comparison on the same changes: useful findings, false alarms, reviewer minutes, environment/setup time and recurring maintenance. |
| Deliverable 4 | Portable decision/feedback records that retain which context and check alternatives were available at decision time; customer-controlled, no training permission implied. |
| Delivery | Repository files and local report, no hosted account or new system of record required. |
| Buyer time | 45-minute kickoff, about 60–120 minutes reviewing cases/ground truth, and 30-minute readout; log actual time. No assumed free maintainer labor. |
| Faber time cap | Aim for 8–12 delivery hours for the full pilot after templates exist; first pilot may reveal that this is infeasible. Stop/re-scope rather than hide labor. |
| Prerequisites | A reproducible permitted environment; owner can define acceptance; accessible evidence; agreement on any private code/data handling; existing CI maintained by the customer. |
| Completion | Agreed matrix and evidence package delivered, limitations and untested cases explicit, reproducible improvements reviewed. Commercial success criteria are separate below. |

**Lower-commitment diagnostic — €250**, credited against the €1,000 pilot if
continued within 30 days: review three changes, map one evidence gap, provide a
one-page plan and a 30-minute readout. No promise that a gap exists; a substantiated
finding that the existing setup is sufficient is a valid diagnostic result. Target
2–3 hours delivery, not a free bespoke integration disguised as discovery.

Faber's existing Proof package is optional. The service can deliver useful regression
tests and evidence policy without asking a customer to trust the current local runner
or an independently uncleared audit candidate. If the work would require production
execution, privileged access or a security guarantee, stop and separately scope it.

## Success and exclusions

The buyer agrees on one primary outcome before the pilot: reduce **active reviewer
minutes spent reconstructing acceptance evidence**, or resolve an identified recurring
coverage gap. Measure paired cases with identical available inputs. Total economic
cost includes setup, owner clarification, check runtime, false-positive review and
ongoing policy upkeep. Merge latency is secondary because queues and PR size confound it.

Commercial continuation requires a useful result **and** a paid renewal or second
purchase. A practical pilot threshold is at least 20% less active evidence-review time
on the agreed sample, without dropping a mandatory scenario or missing a known
serious regression, or an owner-valued newly executable invariant that justifies the
price. The sample cannot prove a production false-accept rate. Report raw outcomes,
not a safety certification.

Use separate blinded reviewers or counterbalanced comparable cases to reduce memory
and order effects. Historical replay establishes feasibility; confirm time savings
on prospective work before claiming an ongoing productivity result. Compare against
the customer's actual review product, including runtime validation if already used.

Excluded: autonomous merges/releases, universal correctness claims, unknown-code
execution on the founder's host, hosted CI replacement, new marketplace/payment
infrastructure, private chain-of-thought, training on customer records by default,
automatic risk-policy relaxation, indefinite custom harness development and outreach
to upstream maintainers on the buyer's behalf.

## From first euro to repeatable revenue

| Goal | Shortest credible route | Proof that it happened |
|---|---|---|
| First €1 | A real customer purchases the €250 diagnostic; no token €1 sale to a friend and no fake marketplace settlement. | Actual approved payment/invoice record maintained through ordinary business operations. |
| First €1,000 | Sell one full pilot, or convert the diagnostic with €750 remaining. Four unrelated diagnostics also produce €1,000 but give weaker evidence of recurring value. | Paid engagement plus accepted delivered work, with founder hours recorded. |
| Repeatability | Three independent buyers in one task family, two renewals/second purchases, similar outputs and bounded setup/upkeep. | Revenue and renewal records plus actual contribution margin; no extrapolation from expressions of interest. |
| Recurring offer | Hypothesis €250–€750/repo/month for a defined change volume, check maintenance and evidence review; price only after workload is known. | Buyer requests ongoing coverage and pays for it. Sell no unlimited-review promise. |

Illustrative economics, not measured margin: a €1,000 pilot taking 10 founder hours
at a chosen €60/hour opportunity cost plus €50 compute has €350 contribution before
sales/admin/tax; 20 hours would make that negative. A €500/month maintenance offer
with two hours labor and €30 compute leaves €350 before overhead, but six hours leaves
€110. This is why support hours and repeatability can kill the product even if checks
are technically useful. Replace every assumption with actual customer data.

Learning may improve retention if later reviews require fewer repeated clarifications,
checks remain relevant and required coverage stays intact. Retrieval may deliver that
benefit without training. The paid promise is lower total acceptance effort, not a
custom model or a quantity of collected trajectories.

## Discovery script and qualification

Javier's first action is to select a reachable engineering lead and show one concrete
example from the repository studies plus the pilot outline. No warm lead is assumed.
If none is available, spend the first week identifying ten public organizations of
the archetype, then have Javier choose and initiate contact. Codex has not contacted
anyone and needs explicit authorization to send messages.

Ask for evidence of the job before explaining the architecture:

1. Walk through the last change where CI was green but acceptance still took work.
2. Which scenario, environment or sign-off had to be reconstructed? How often does
   this happen, and who spends time on it?
3. Show the existing agent/review/CI setup. What has already been tried? Could a short
   script or a better test solve the whole problem?
4. Which upcoming change family has a real deadline and owner? What evidence could
   be shared lawfully, with no production access?
5. Would that owner buy the €250 diagnostic or €1,000 pilot now? If not, record the
   objection in their terms; a hypothetical future price is not willingness to pay.

Suggested outreach text for Javier to adapt, **not sent**:

> I am testing a small service for teams whose agent-assisted maintenance changes
> still take senior time to verify. For one repo, I map required acceptance evidence,
> find skipped or missing coverage, and leave reusable checks in your existing CI.
> The diagnostic is €250; a two-week pilot is €1,000 with the diagnostic credited.
> Could we walk through one recent change to see whether your current tools already
> solve this? If they do, I will say so.

## Human-only gates and autonomous preparation

Javier must choose a real prospect, authorize/initiate contact, agree scope and lawful
data access, and handle the commercial commitment and payment. None is implied by a
public repository or a vendor logo. These gates do not prevent Codex from preparing
source-backed examples, a read-only demo, measurement forms and tests.

Codex's next useful work is to validate the first buyer-supplied case, preserve the
proposal-time evidence, and compare the existing static policy and frontier+retrieval
baseline before creating checks. If no buyer supplies cases, use the public study
records to evaluate data reconstruction and documentation, not to invent traction.

## Kill criteria

- After ten qualified conversations and explicit offers, no payment or concrete
  purchase process: revise offer once from objections. After ten more, stop B as
  a near-term revenue wedge unless a materially new buyer signal appears.
- Buyers cannot supply examples or quantify even approximate repeated effort:
  disqualify that segment rather than designing a platform for it.
- Median setup exceeds a working day per repo, or two small improvements need more
  than two days of bespoke harness work: narrow the task family or raise a quoted
  service price; do not call the result self-serve software.
- Maintenance consumes most review savings, or an existing agent+CI change is equally
  useful and cheaper: keep the simpler solution and drop the recurring product.
- Three useful pilots but no repeat purchases: operate as a one-off service or return
  to research; do not build hosting to manufacture retention.
