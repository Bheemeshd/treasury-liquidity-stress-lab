from __future__ import annotations

import unittest

from liquidity_stress.generate import generate_market_rates, generate_positions


class GenerationTests(unittest.TestCase):
    def test_positions_are_deterministic_for_same_seed(self) -> None:
        first = generate_positions(seed=123, count=100)
        second = generate_positions(seed=123, count=100)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 100)

    def test_different_seed_changes_positions(self) -> None:
        first = generate_positions(seed=123, count=20)
        second = generate_positions(seed=124, count=20)
        self.assertNotEqual(first, second)

    def test_generated_data_respects_core_controls(self) -> None:
        rows = generate_positions(seed=99, count=200)
        self.assertEqual(len({row["position_id"] for row in rows}), len(rows))
        self.assertTrue(all(row["principal_eur"] > 0 for row in rows))
        self.assertTrue(all(row["currency"] in {"EUR", "USD", "GBP", "CHF"} for row in rows))
        self.assertTrue(
            all(row["hqla_level"] == "None" for row in rows if row["side"] == "Liability")
        )
        self.assertTrue(all(row["runoff_weight_pct"] == 0 for row in rows if row["side"] == "Asset"))

    def test_market_rate_shape(self) -> None:
        rates = generate_market_rates(seed=5)
        self.assertEqual(len(rates), 72)
        self.assertEqual(len({row["rate_date"] for row in rates}), 24)
        self.assertTrue(all(row["rate_pct"] > 0 for row in rates))

    def test_minimum_position_count_is_enforced(self) -> None:
        with self.assertRaises(ValueError):
            generate_positions(count=19)


if __name__ == "__main__":
    unittest.main()

