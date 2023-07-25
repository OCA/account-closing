# Copyright 2023 Foodles (https://www.foodles.co/)
# @author: Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import datetime

from freezegun import freeze_time
from parameterized import parameterized

from odoo.tests import tagged

from .common import CommonAccountInvoiceCutoffCase


@tagged("-at_install", "post_install")
class TestAccountMoveLine(CommonAccountInvoiceCutoffCase):
    @parameterized.expand(
        [
            ("Two months", "2023-01-08", "2023-01-01", "2023-02-28", True),
            ("Next month", "2023-01-08", "2023-02-01", "2023-02-28", True),
            ("Same month", "2023-02-08", "2023-02-01", "2023-02-28", False),
        ]
    )
    def test_account_move_line_has_deferred_dates(
        self,
        _test_name,
        invoice_date,
        start_date,
        end_date,
        expected_has_deferred_dates,
    ):
        self.invoice.date = invoice_date
        move_line = self.invoice.line_ids[0]
        move_line.start_date = start_date
        move_line.end_date = end_date
        self.assertEqual(move_line.has_deferred_dates(), expected_has_deferred_dates)

    @parameterized.expand(
        [
            (
                "Two months",
                "2023-01-08",
                "2023-01-01",
                "2023-02-28",
                False,
                False,
                True,
            ),
            (
                "Next month",
                "2023-01-08",
                "2023-02-01",
                "2023-02-28",
                False,
                False,
                True,
            ),
            (
                "month before",
                "2023-02-01",
                "2023-01-01",
                "2023-01-31",
                False,
                False,
                False,
            ),
            (
                "Next month already generated",
                "2023-01-08",
                "2023-02-01",
                "2023-02-28",
                False,
                True,
                False,
            ),
            (
                "Same month",
                "2023-02-08",
                "2023-02-01",
                "2023-02-28",
                False,
                False,
                False,
            ),
            (
                "No cut-off account",
                "2023-01-08",
                "2023-01-01",
                "2023-02-28",
                True,
                False,
                False,
            ),
            # Testing end date or start date false alone is not a possible case
            # because existing constraints
            ("No start/end date", "2023-01-08", False, False, False, False, False),
        ]
    )
    def test_account_move_line_is_deferrable_line(
        self,
        _test_name,
        invoice_date,
        start_date,
        end_date,
        without_cutoff_account,
        already_generated,
        expected_is_deferrable_line,
    ):
        if without_cutoff_account:
            self.account_revenue.deferred_accrual_account_id = False
        self.invoice.date = invoice_date
        move_line = self.invoice.line_ids[0]
        move_line.write(
            {
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        if already_generated:
            with freeze_time(invoice_date):
                self.invoice.action_post()
        self.assertEqual(move_line.is_deferrable_line, expected_is_deferrable_line)

    @parameterized.expand(
        [
            (
                "1 to 15 jan",
                datetime.date(2023, 1, 1),
                datetime.date(2023, 1, 1),
                datetime.date(2023, 1, 15),
                (
                    datetime.date(2023, 1, 1),
                    datetime.date(2023, 1, 15),
                ),
            ),
            (
                "15 to 15 jan",
                datetime.date(2023, 1, 1),
                datetime.date(2023, 1, 15),
                datetime.date(2023, 1, 15),
                (
                    datetime.date(2023, 1, 15),
                    datetime.date(2023, 1, 15),
                ),
            ),
            (
                "15 to 31 jan",
                datetime.date(2023, 1, 1),
                datetime.date(2023, 1, 15),
                datetime.date(2023, 2, 15),
                (
                    datetime.date(2023, 1, 15),
                    datetime.date(2023, 1, 31),
                ),
            ),
            (
                "1 to 15 feb",
                datetime.date(2023, 2, 1),
                datetime.date(2023, 1, 15),
                datetime.date(2023, 2, 15),
                (
                    datetime.date(2023, 2, 1),
                    datetime.date(2023, 2, 15),
                ),
            ),
            (
                "month in the middle: 1 to 28 feb",
                datetime.date(2023, 2, 1),
                datetime.date(2023, 1, 15),
                datetime.date(2023, 3, 15),
                (
                    datetime.date(2023, 2, 1),
                    datetime.date(2023, 2, 28),
                ),
            ),
            (
                "No matched on this next period",
                datetime.date(2023, 2, 1),
                datetime.date(2023, 1, 15),
                datetime.date(2023, 1, 15),
                (
                    None,
                    None,
                ),
            ),
            (
                "No matched on the previous period",
                datetime.date(2022, 12, 1),
                datetime.date(2023, 1, 15),
                datetime.date(2023, 1, 15),
                (
                    None,
                    None,
                ),
            ),
        ]
    )
    def test_get_period_start_end_dates(
        self, _test_name, period, line_start, line_end, expected_start_end
    ):

        move_line = self.invoice.line_ids[0]
        move_line.write({"start_date": line_start, "end_date": line_end})
        self.assertEqual(
            move_line._get_period_start_end_dates(period), expected_start_end
        )

    @parameterized.expand(
        [
            (
                "no change",
                {
                    datetime.date(2022, 12, 1): 2400,
                    datetime.date(2023, 1, 1): 2400,
                },
                {
                    datetime.date(2022, 12, 1): 2400.0,
                    datetime.date(2023, 1, 1): 2400.0,
                },
            ),
            (
                "fix rounding",
                {
                    datetime.date(2022, 12, 1): 2400.01,
                    datetime.date(2023, 1, 1): 2400.01,
                },
                {
                    datetime.date(2022, 12, 1): 2399.99,
                    datetime.date(2023, 1, 1): 2400.01,
                },
            ),
            (
                "rounds 2 periods",
                {
                    datetime.date(2022, 12, 1): 2400.00666,
                    datetime.date(2023, 1, 1): 2400.00666,
                },
                {
                    datetime.date(2022, 12, 1): 2399.99,
                    datetime.date(2023, 1, 1): 2400.01,
                },
            ),
            (
                "rounds 3 periods",
                {
                    datetime.date(2022, 12, 1): 1600.00666,
                    datetime.date(2023, 1, 1): 1600.00666,
                    datetime.date(2023, 2, 1): 1600.00666,
                },
                {
                    datetime.date(2022, 12, 1): 1599.98,
                    datetime.date(2023, 1, 1): 1600.01,
                    datetime.date(2023, 2, 1): 1600.01,
                },
            ),
            (
                "rounds 1 period",
                {
                    datetime.date(2022, 12, 1): 4800.0003,
                },
                {
                    datetime.date(2022, 12, 1): 4800.00,
                },
            ),
            (
                "rounds nothing",
                {},
                {},
            ),
        ]
    )
    def test_round_amounts(self, _test_name, periods_amounts, expected_periods_amounts):
        move_line = self.invoice.line_ids[0]
        results = move_line._round_amounts(periods_amounts)
        for expected_key, expected_value in expected_periods_amounts.items():
            self.assertAlmostEqual(
                results[expected_key],
                expected_value,
                2,
            )

    @parameterized.expand(
        [
            (
                "No changes",
                {
                    datetime.date(2023, 1, 1): 1600.0,
                    datetime.date(2023, 2, 1): 1600.0,
                    datetime.date(2023, 3, 1): 1600.0,
                },
                [
                    datetime.date(2023, 1, 1),
                    datetime.date(2023, 2, 1),
                    datetime.date(2023, 3, 1),
                ],
                {
                    datetime.date(2023, 1, 1): 1600.0,
                    datetime.date(2023, 2, 1): 1600.0,
                    datetime.date(2023, 3, 1): 1600.0,
                },
            ),
            (
                "One previous",
                {
                    datetime.date(2022, 12, 1): 1600.0,
                    datetime.date(2023, 1, 1): 1600.0,
                    datetime.date(2023, 2, 1): 1600.0,
                    datetime.date(2023, 3, 1): 1600.0,
                },
                [
                    datetime.date(2023, 1, 1),
                    datetime.date(2023, 2, 1),
                    datetime.date(2023, 3, 1),
                ],
                {
                    datetime.date(2023, 1, 1): 3200.0,
                    datetime.date(2023, 2, 1): 1600.0,
                    datetime.date(2023, 3, 1): 1600.0,
                },
            ),
            (
                "One after",
                {
                    datetime.date(2023, 1, 1): 1600.0,
                    datetime.date(2023, 2, 1): 1600.0,
                    datetime.date(2023, 3, 1): 1600.0,
                    datetime.date(2023, 4, 1): 1600.0,
                },
                [
                    datetime.date(2023, 1, 1),
                    datetime.date(2023, 2, 1),
                    datetime.date(2023, 3, 1),
                ],
                {
                    datetime.date(2023, 1, 1): 1600.0,
                    datetime.date(2023, 2, 1): 1600.0,
                    datetime.date(2023, 3, 1): 3200.0,
                },
            ),
            (
                "one ok",
                {
                    datetime.date(2023, 1, 1): 1600.0,
                },
                [
                    datetime.date(2023, 1, 1),
                ],
                {
                    datetime.date(2023, 1, 1): 1600.0,
                },
            ),
            (
                "one period before",
                {
                    datetime.date(2022, 1, 1): 1600.0,
                },
                [
                    datetime.date(2023, 1, 1),
                    datetime.date(2023, 2, 1),
                    datetime.date(2023, 3, 1),
                ],
                {
                    datetime.date(2023, 1, 1): 1600.0,
                    # as long we are using defaultdict
                    # this is ok
                    # datetime.date(2023, 2, 1): 0.0,
                    datetime.date(2023, 3, 1): 0.0,
                },
            ),
            (
                "one period after",
                {
                    datetime.date(2024, 1, 1): 1600.0,
                },
                [
                    datetime.date(2023, 1, 1),
                    datetime.date(2023, 2, 1),
                ],
                {
                    datetime.date(2023, 1, 1): 0.0,
                    datetime.date(2023, 2, 1): 1600.0,
                },
            ),
            (
                "multiple before-after",
                {
                    datetime.date(2022, 1, 1): 1600.0,
                    datetime.date(2022, 2, 1): 1600.0,
                    datetime.date(2022, 6, 1): 1600.0,
                    datetime.date(2022, 7, 1): 1600.0,
                },
                [
                    datetime.date(2023, 4, 1),
                ],
                {
                    datetime.date(2023, 4, 1): 6400.0,
                },
            ),
            (
                "no amounts",
                {},
                [
                    datetime.date(2023, 3, 1),
                    datetime.date(2023, 4, 1),
                ],
                {
                    datetime.date(2023, 3, 1): 0.0,
                    datetime.date(2023, 4, 1): 0.0,
                },
            ),
        ]
    )
    def test_line_amounts_on_proper_periods(
        self, _name, line_amounts, periods, expected
    ):
        self.assertEqual(
            dict(
                self.env["account.move.line"]._line_amounts_on_proper_periods(
                    line_amounts, periods
                )
            ),
            expected,
        )

    @parameterized.expand(
        [
            (
                "Case A",
                None,
                {
                    datetime.date(2023, 1, 1): 1600.0,
                    datetime.date(2023, 2, 1): 1600.0,
                    datetime.date(2023, 3, 1): 1600.0,
                },
            ),
            (
                "Case B",
                None,
                {
                    datetime.date(2023, 1, 1): 40.0,
                    datetime.date(2023, 2, 1): 40.0,
                    datetime.date(2023, 3, 1): 40.0,
                },
            ),
            (
                "Case C",
                None,
                {
                    datetime.date(2023, 1, 1): 0.0,
                    datetime.date(2023, 2, 1): 30.0,
                    datetime.date(2023, 3, 1): 30.0,
                },
            ),
            (
                "Case D",
                None,
                {
                    datetime.date(2023, 1, 1): 130.0,
                    datetime.date(2023, 2, 1): 130.0,
                    datetime.date(2023, 3, 1): 0.0,
                },
            ),
            (
                "Case E",
                None,
                {
                    datetime.date(2023, 1, 1): 113.5,
                    # because defaultdict
                    # datetime.date(2023, 2, 1): 0.0,
                    datetime.date(2023, 3, 1): 0.0,
                },
            ),
            (
                "Case F",
                None,
                {
                    datetime.date(2023, 1, 1): 518.0,
                    # because defaultdict
                    datetime.date(2023, 2, 1): 259.0,
                    datetime.date(2023, 3, 1): 0.0,
                },
            ),
            (
                "Case G",
                None,
                {
                    datetime.date(2023, 1, 1): 0,
                    # because defaultdict
                    # datetime.date(2023, 2, 1): 0.0,
                    datetime.date(2023, 3, 1): 255,
                },
            ),
            (
                "Case G",
                [
                    datetime.date(2023, 1, 1),
                    datetime.date(2023, 2, 1),
                    datetime.date(2023, 3, 1),
                    datetime.date(2023, 4, 1),
                    datetime.date(2023, 5, 1),
                ],
                {
                    datetime.date(2023, 1, 1): 0.0,
                    datetime.date(2023, 5, 1): 255.0,
                },
            ),
            (
                "Case I",
                None,
                {
                    datetime.date(2023, 1, 1): 666.66,
                    datetime.date(2023, 2, 1): 666.67,
                    datetime.date(2023, 3, 1): 666.67,
                },
            ),
        ]
    )
    def test_get_amounts_per_periods_equals(self, line_case, periods, expected):

        if not periods:
            periods = [
                datetime.date(2023, 1, 1),
                datetime.date(2023, 2, 1),
                datetime.date(2023, 3, 1),
            ]
        move_line = self.invoice.line_ids.filtered(
            lambda line: line.name.startswith(line_case)
        )
        move_line.cutoff_method = "equal"
        self.assertEqual(move_line._get_amounts_per_periods(periods), expected)

    @parameterized.expand(
        [
            (
                "Case A",
                None,
                {
                    datetime.date(2023, 1, 1): 1379.32,
                    datetime.date(2023, 2, 1): 1710.34,
                    datetime.date(2023, 3, 1): 1710.34,
                },
            ),
            (
                "Case B",
                None,
                {
                    datetime.date(2023, 1, 1): 40.0,
                    datetime.date(2023, 2, 1): 40.0,
                    datetime.date(2023, 3, 1): 40.0,
                },
            ),
            (
                "Case C",
                None,
                {
                    datetime.date(2023, 1, 1): 0.0,
                    datetime.date(2023, 2, 1): 30.0,
                    datetime.date(2023, 3, 1): 30.0,
                },
            ),
            (
                "Case D",
                None,
                {
                    datetime.date(2023, 1, 1): 130.0,
                    datetime.date(2023, 2, 1): 130.0,
                    datetime.date(2023, 3, 1): 0.0,
                },
            ),
            (
                "Case E",
                None,
                {
                    datetime.date(2023, 1, 1): 113.5,
                    # datetime.date(2023, 2, 1): 0.0,
                    datetime.date(2023, 3, 1): 0.0,
                },
            ),
            (
                "Case F",
                None,
                {
                    datetime.date(2023, 1, 1): 518.0,
                    datetime.date(2023, 2, 1): 259.0,
                    datetime.date(2023, 3, 1): 0.0,
                },
            ),
            (
                "Case G",
                None,
                {
                    datetime.date(2023, 1, 1): 0,
                    # datetime.date(2023, 2, 1): 0.0,
                    datetime.date(2023, 3, 1): 255,
                },
            ),
            (
                "Case G",
                [
                    datetime.date(2023, 1, 1),
                    datetime.date(2023, 2, 1),
                    datetime.date(2023, 3, 1),
                    datetime.date(2023, 4, 1),
                    datetime.date(2023, 5, 1),
                ],
                {
                    datetime.date(2023, 1, 1): 0.0,
                    datetime.date(2023, 5, 1): 255.0,
                },
            ),
            (
                "Case I",
                None,
                {
                    datetime.date(2023, 1, 1): 491.81,
                    datetime.date(2023, 2, 1): 1016.39,
                    datetime.date(2023, 3, 1): 491.80,
                },
            ),
        ]
    )
    def test_get_amounts_per_periods_monthly_prorata(
        self, line_case, periods, expected
    ):

        if not periods:
            periods = [
                datetime.date(2023, 1, 1),
                datetime.date(2023, 2, 1),
                datetime.date(2023, 3, 1),
            ]
        move_line = self.invoice.line_ids.filtered(
            lambda line: line.name.startswith(line_case)
        )
        move_line.cutoff_method = "monthly_prorata_temporis"
        result = move_line._get_amounts_per_periods(periods)
        for period, expected_amount in expected.items():
            self.assertAlmostEqual(result[period], expected_amount, 2)

    def test_prepare_entry_lines_with_null_amount(self):
        self.assertFalse(
            self.invoice.line_ids[0]._prepare_entry_lines(self.invoice, None, 0)
        )
