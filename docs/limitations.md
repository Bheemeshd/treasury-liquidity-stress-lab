# Limitations and production roadmap

## What this model does not claim

This is a synthetic analytics demonstration. It is **not** a regulatory LCR engine, IRRBB measurement system, ILAAP, ALM platform, liquidity risk appetite report, stress-test submission, or accounting forecast.

## Material simplifications

| Area | Portfolio-model simplification | Production enhancement |
|---|---|---|
| Data | Seeded synthetic positions | Governed feeds from core banking, treasury, collateral, derivatives, and market-data systems |
| Behaviour | Template runoff and inflow weights | Empirical decay/prepayment models, segmentation, back-testing, and model risk approval |
| HQLA | Four simplified factors; no composition caps | Jurisdiction-specific eligibility, operational requirements, Level 2 caps, collateral location, and monetisation tests |
| Funding | Simple contractual/non-maturity split | Secured/unsecured mechanics, collateral swaps, margin calls, facilities, and rollover probability |
| Currency | All values translated to EUR | Significant-currency ladders, FX convertibility, swap markets, trapped liquidity, and legal-entity transfer restrictions |
| Cash flows | Principal-only tenor ladder | Interest, fees, coupons, amortisation schedules, optionality, derivatives, and intraday liquidity |
| Rates | Parallel shock with simple betas | Full yield curves, basis risk, administered-rate models, dynamic balance sheet, EVE, and optionality |
| Survival | Buffer/outflow scaling proxy | Daily dynamic survival horizon with counterbalancing capacity and contingency actions |
| Scenarios | Five illustrative cases | Governance-approved idiosyncratic, market-wide, and combined stresses with reverse stress testing |
| Reporting | Local CSV/SQLite/Streamlit | Access control, lineage catalog, audit history, approvals, observability, and controlled deployment |

## Interpretation cautions

- The synthetic portfolio is calibrated to create an analytically useful binding severe scenario; the result is not evidence about any real bank.
- The 100% line is a familiar analytical reference, not proof of compliance or a management limit.
- Positive ΔNII under a rising-rate scenario can coexist with material liquidity stress and should never be read as a risk offset without a joint framework.
- A negative post-buffer gap is a model signal, not a forecast of default or failure.
- `survival_days_proxy` is capped at 365 for display and should not be interpreted as a dynamic survival horizon.
- Scenario betas and multipliers are illustrative assumptions, not calibrated estimates.

## Prioritized production roadmap

1. Add position-level contractual schedules and daily 90-day cash-flow ladders.
2. Calibrate deposit decay, loan prepayment, and wholesale renewal using historical cohorts.
3. Separate calculations by currency and legal entity before applying transferability constraints.
4. Extend the buffer engine with eligibility rules, Level 2 caps, collateral encumbrance, and monetisation evidence.
5. Add secured funding, derivatives, collateral calls, committed facilities, and contingency actions.
6. Implement non-parallel rate curves, deposit floors, basis risk, EVE, and dynamic NII.
7. Introduce assumption versioning, maker-checker approval, back-testing, thresholds, and model governance.
8. Deploy to a governed warehouse with orchestration, lineage, access control, monitoring, and immutable reporting snapshots.

