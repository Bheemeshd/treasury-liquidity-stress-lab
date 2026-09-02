# Methodology

## Objective

The model provides a transparent, educational view of two linked treasury questions:

- Can a simplified liquid-asset buffer cover stressed net cash outflows over 30 days?
- How might the same balance sheet's one-year net interest income respond to a parallel rate shock?

It favors traceability over regulatory completeness. Each formula is implemented in small Python functions and, for the coverage metric, independently in SQL.

## 1. Synthetic portfolio generation

The default run creates 900 records with a 54/46 asset-liability position split. Weighted templates create realistic product variety without replicating any institution:

- Assets: cash/reserves, sovereign and covered bonds, interbank placements, retail mortgages, SME loans, and corporate loans.
- Liabilities: current and term retail deposits, SME operational deposits, corporate deposits, wholesale funding, covered bond funding, and interbank borrowing.

The random generator is seeded (`20260902`), making every value reproducible. Position amounts, rates, currency, maturity, repricing, HQLA level, and encumbrance are generated within documented bounds.

## 2. Eligible liquidity buffer

Simplified base factors are applied to unencumbered assets:

| Classification | Base factor |
|---|---:|
| Level 1 | 100% |
| Level 2A | 85% |
| Level 2B | 50% |
| None / encumbered | 0% |

For scenario `s` and position `i`:

```text
adjusted factor(i,s) = max(0, base factor(i) − haircut add-on(s))
eligible buffer(s) = Σ principal(i) × adjusted factor(i,s)
```

This is a monetisable-buffer proxy; it does not implement regulatory Level 2 composition caps.

## 3. Stressed 30-day outflows

- Non-maturity liabilities are included regardless of their modelled day-1 behavioural maturity.
- Contractual liabilities are included when maturity is 30 days or less.
- Retail positions use the retail multiplier; other liability segments use the wholesale multiplier.
- The position-level stressed runoff rate is capped at 100%.

```text
outflow(i,s) = principal(i) × min(100%, base runoff(i) × segment multiplier(s))
```

## 4. Stressed 30-day inflows and cap

Contractual non-HQLA assets maturing within 30 days generate inflows:

```text
raw inflow(i,s) = principal(i) × inflow weight(i) × inflow multiplier(s)
recognised inflows(s) = min(raw inflows(s), 75% × outflows(s))
net outflows(s) = max(outflows(s) − recognised inflows(s), €1)
```

The €1 floor prevents division by zero in edge-case synthetic samples; it is immaterial for the delivered dataset.

## 5. LCR-style proxy and liquidity measures

```text
coverage proxy(s) = eligible buffer(s) / net outflows(s) × 100
liquidity surplus(s) = eligible buffer(s) − net outflows(s)
survival-days proxy(s) = min(365, 30 × eligible buffer(s) / net outflows(s))
```

The 100% line is an **illustrative reference**, not a claim of regulatory compliance.

## 6. Cash-flow gap ladder

Each position is mapped by `maturity_days` to one of six mutually exclusive buckets. Non-HQLA asset cash flows use their stressed inflow weight. Liability flows use stressed runoff, capped at principal. For each bucket:

```text
net gap = stressed inflows − stressed outflows
cumulative gap(t) = cumulative gap(t−1) + net gap(t)
post-buffer gap(t) = cumulative gap(t) + eligible buffer
```

This makes the distinction between contractual/behavioural mismatch and immediately available liquidity explicit.

## 7. One-year NII sensitivity

Base annual NII is a static-balance interest-income-minus-expense estimate:

```text
base NII = Σ asset principal × asset rate − Σ liability principal × liability rate
```

Rate sensitivity applies to the portion of the coming year after the next repricing date:

```text
exposure fraction(i) = max(0, (365 − repricing days(i)) / 365)
ΔNII asset(i,s) = principal × shock(s) × asset beta(s) × exposure fraction
ΔNII liability(i,s) = −principal × shock(s) × deposit beta(s) × exposure fraction
projected NII(s) = base NII + Σ ΔNII(i,s)
```

Fixed-rate balances reprice at maturity in the generated data; positions beyond one year have zero one-year sensitivity.

## 8. Scenarios

| Scenario | Retail runoff | Wholesale runoff | Inflow recognition | HQLA add-on | Rate shock |
|---|---:|---:|---:|---:|---:|
| Baseline | 1.0× | 1.0× | 100% | 0 pp | 0 bps |
| Retail Deposit Run | 2.5× | 1.15× | 90% | 2 pp | +50 bps |
| Wholesale Funding Freeze | 1.1× | 3.0× | 85% | 5 pp | +100 bps |
| Rates +200 bps | 1.0× | 1.0× | 100% | 1 pp | +200 bps |
| Combined Severe | 2.5× | 3.0× | 70% | 12 pp | +250 bps |

Pass-through betas are also scenario-specific; see `config/scenarios.json` for the controlled values.

## 9. Validation approach

- Unit tests verify determinism, data bounds, inflow caps, encumbrance exclusion, haircut arithmetic, NII direction, and tenor reconciliation.
- The integration test generates a new portfolio in a temporary directory, creates the database, runs all scenarios, and validates output counts/artifacts.
- Python and SQL versions of the coverage proxy must reconcile to two decimal places for all scenarios.

