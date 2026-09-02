# Recruiter and interview talking points

## 30-second project pitch

“I built a banking treasury analytics product using a fully synthetic 900-position balance sheet. A reproducible Python pipeline loads constrained SQLite tables, stresses funding runoff, inflows, liquid-asset haircuts, and rates, then produces an LCR-style proxy, maturity gaps, and one-year NII sensitivity. The key insight was that the portfolio looked strong at 214% in baseline but fell to 80% in Combined Severe due mainly to wholesale funding concentration. I delivered the analysis in Streamlit, reconciled Python to SQL, and added 11 automated tests and CI.”

## Resume bullets

- Built an end-to-end treasury stress-testing data product in **Python, SQL, SQLite, and Streamlit**, modelling 900 synthetic balance-sheet positions across 5 liquidity/rate scenarios and 6 tenor buckets.
- Identified wholesale funding concentration as the binding risk: coverage declined from **214.4% baseline to 79.7% in Combined Severe**, creating a **€109.8m modelled shortfall** and actionable contingency-funding target.
- Engineered a reproducible, controlled pipeline with seeded generation, schema constraints, SQL/Python reconciliation, **11 automated tests**, GitHub Actions CI, and executive/technical documentation.

## LinkedIn project description

I built a Treasury Liquidity & Interest-Rate Stress Lab to demonstrate end-to-end banking analytics. The project generates a reproducible synthetic balance sheet, loads it into SQLite, and evaluates 30-day liquidity coverage, cash-flow gaps, and one-year NII sensitivity under five scenarios. The dashboard shows how wholesale funding stress can turn a 214.4% baseline coverage position into a 79.7% severe result—even while rising rates improve modelled NII. The repository includes transparent formulas, SQL reconciliation, automated tests, CI, documentation, and a clear non-regulatory boundary.

## Likely interview questions

### Why did you call it an LCR-style proxy instead of LCR?

Because the broad buffer/net-outflow structure is useful for analysis, but the model does not implement jurisdiction-specific HQLA eligibility, Level 2 caps, secured funding, derivatives, operational deposits, currency constraints, and other rule details. Naming the boundary is part of responsible analytics.

### Why cap inflows at 75%?

It prevents assumed receivables from eliminating the need to maintain a liquidity buffer. In this project it is a transparent simplifying rule and is explicitly tested; it should not be taken as a complete regulatory implementation.

### What drives the severe result?

Non-retail runoff is multiplied by 3, inflows fall to 70%, and the HQLA factor receives a 12 percentage-point haircut add-on. Net outflows rise from €229.1m to €539.6m while the usable buffer falls from €491.0m to €429.8m.

### Why is ΔNII positive when rates rise?

Within the modelled one-year horizon, more asset principal reprices and the scenario asset pass-through is stronger than liability pass-through. That is a directional static-balance result; a production model would add curve shape, deposit floors, basis risk, optionality, and dynamic business volumes.

### How did you validate the result?

I tested component formulas and edge cases, generated a fresh temporary database in the integration test, and independently implemented the coverage calculation as a SQLite view. All five Python scenario ratios reconcile to SQL at two decimal places.

### What would you productionize first?

Daily contractual cash flows and empirical behavioural calibration, followed by significant-currency/legal-entity views and secured funding/derivatives. Those changes materially improve decision usefulness before investing in UI scale.

## Portfolio positioning

This project demonstrates a combination recruiters often look for in banking analysts: domain awareness, SQL/Python execution, transparent assumptions, data controls, clear visualization, and the ability to turn numbers into management actions without overstating model precision.
