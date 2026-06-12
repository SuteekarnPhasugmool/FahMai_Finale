import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agentic_ai"))

from format_submission import format_rows, parse_markdown_table


class FormatSubmissionTest(unittest.TestCase):
    def test_parse_markdown_table_preserves_escaped_pipe_values(self):
        headers, rows = parse_markdown_table(
            "\n".join(
                [
                    "| related_entity_id | amount_thb |",
                    "| --- | --- |",
                    "| REMOTE\\|2025-07-15\\|credit_card | 18,906,765.00 |",
                ]
            )
        )

        self.assertEqual(headers, ["related_entity_id", "amount_thb"])
        self.assertEqual(rows[0]["related_entity_id"], "REMOTE|2025-07-15|credit_card")

    def test_format_rows_uses_column_shape_not_question_id(self):
        answer = "\n".join(
            [
                "| campaign_id | description_en | transaction_count | net_total_thb | discount_total_thb | roi_ratio |",
                "| --- | --- | --- | --- | --- | --- |",
                "| SF-LAUNCH-2568 | SF Galaxy Pro 2568 launch promo | 3749 | 143,301,515.00 | 7,542,185.00 | 19.00 |",
            ]
        )

        formatted = format_rows("Which campaign has the highest ROI ratio?", answer)

        self.assertEqual(formatted, "(SF-LAUNCH-2568, 19.0x)")


if __name__ == "__main__":
    unittest.main()
