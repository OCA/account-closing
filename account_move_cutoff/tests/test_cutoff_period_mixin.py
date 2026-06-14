# Copyright 2023 Foodles (https://www.foodles.co/)
# @author: Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import datetime

from parameterized import parameterized

from odoo.tests import tagged

from .common import CommonAccountInvoiceCutoffCase


@tagged("-at_install", "post_install")
class TestCutoffPeriodMixin(CommonAccountInvoiceCutoffCase):
    @parameterized.expand(
        [
            (datetime.date(2023, 1, 1), datetime.date(2023, 1, 1)),
            (datetime.date(2023, 1, 8), datetime.date(2023, 1, 1)),
            (datetime.datetime(2023, 1, 1, 2, 3), datetime.date(2023, 1, 1)),
            (datetime.datetime(2023, 1, 8, 3, 1), datetime.date(2023, 1, 1)),
        ]
    )
    def test_period_from_date(self, test_date, expected_first_of_month):
        self.assertEqual(
            self.env["account.move"]._period_from_date(test_date),
            expected_first_of_month,
        )

    @parameterized.expand(
        [
            (datetime.date(2023, 1, 8), datetime.date(2023, 1, 31)),
            (datetime.date(2023, 1, 31), datetime.date(2023, 1, 31)),
            (datetime.date(2023, 12, 31), datetime.date(2023, 12, 31)),
            (datetime.datetime(2023, 2, 1, 2, 3), datetime.date(2023, 2, 28)),
            (datetime.datetime(2023, 2, 28, 3, 1), datetime.date(2023, 2, 28)),
        ]
    )
    def test_last_day_of_month(self, test_date, expected_last_of_month):
        self.assertEqual(
            self.env["account.move"]._last_day_of_month(test_date),
            expected_last_of_month,
        )

    @parameterized.expand(
        [
            (
                datetime.date(2023, 1, 1),
                datetime.date(2023, 1, 31),
                [datetime.date(2023, 1, 1)],
            ),
            (
                datetime.date(2023, 1, 8),
                datetime.date(2023, 1, 28),
                [datetime.date(2023, 1, 1)],
            ),
            (
                datetime.date(2023, 1, 17),
                datetime.date(2023, 3, 18),
                [
                    datetime.date(2023, 1, 1),
                    datetime.date(2023, 2, 1),
                    datetime.date(2023, 3, 1),
                ],
            ),
        ]
    )
    def test_generate_monthly_periods(self, start_date, end_date, expected_periods):
        self.assertEqual(
            self.env["account.move"]._generate_monthly_periods(start_date, end_date),
            expected_periods,
        )
