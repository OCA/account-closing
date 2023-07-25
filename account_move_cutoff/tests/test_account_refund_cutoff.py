# Copyright 2023 Foodles (https://www.foodles.co/)
# @author: Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import date

from freezegun import freeze_time

from odoo.tests import tagged

from .common import CommonAccountCutoffBaseCAse


@tagged("-at_install", "post_install")
class TestRefundCutoff(CommonAccountCutoffBaseCAse):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_revenue = cls.env["account.account"].search(
            [
                (
                    "user_type_id",
                    "=",
                    cls.env.ref("account.data_account_type_revenue").id,
                )
            ],
            limit=1,
        )
        cls.account_revenue.deferred_accrual_account_id = cls.account_cutoff
        cls.sale_journal = cls.env["account.journal"].search(
            [("type", "=", "sale")], limit=1
        )
        cls.refund = cls._create_invoice(
            journal=cls.sale_journal,
            move_type="out_refund",
            account=cls.account_revenue,
        )

    def test_ensure_refund_without_start_end_date_are_postable(self):
        self.refund.line_ids.product_id.must_have_dates = False
        self.refund.line_ids.write({"start_date": False, "end_date": False})
        self.refund.action_post()
        self.assertEqual(self.refund.state, "posted")

    def test_account_refund_cutoff_equals(self):
        # self.env["ir.config_parameter"].set_param(
        #     "account_move_cutoff.default_cutoff_method",
        #     "equal"
        # )
        self.refund.line_ids.cutoff_method = "equal"
        with freeze_time("2023-01-15"):
            self.refund.action_post()
        self.assertEqual(self.refund.cutoff_move_count, 4)

    def test_account_refund_cutoff_monthly_factor_prorata(self):
        self.refund.line_ids.cutoff_method = "monthly_prorata_temporis"

        with freeze_time("2023-01-15"):
            self.refund.action_post()
        self.assertEqual(self.refund.cutoff_move_count, 4)

        cutoff_move = self.refund.cutoff_entry_ids.filtered(
            lambda move, move_date=date(2023, 1, 15): move.date == move_date
        )

        self.assertEqual(cutoff_move.journal_id, self.miscellaneous_journal)
        self.assertEqual(
            cutoff_move.ref,
            f"Advance revenue recognition of {self.refund.name} (01 2023)",
        )
        self.assertAccountMoveLines(
            cutoff_move,
            [
                (
                    lambda ml: ml.credit > 0,
                    {"account_id": self.account_revenue, "debit": 0.0},
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case A" in ml.name,
                    {"credit": 3420.68},
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case B" in ml.name,
                    {"credit": 80.0},
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case C" in ml.name,
                    {"credit": 60.0},
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case D" in ml.name,
                    {"credit": 130.0},
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case F" in ml.name,
                    {"credit": 259.0},
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case G" in ml.name,
                    {"credit": 255.0},
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case I" in ml.name,
                    {"credit": 1508.19},
                ),
                (
                    lambda ml: ml.debit > 0,
                    {"account_id": self.account_cutoff, "credit": 0.0},
                ),
            ],
        )
        self.assertAlmostEqual(
            sum(cutoff_move.line_ids.filtered(lambda ml: ml.debit > 0).mapped("debit")),
            5712.87,
            2,
        )

        deferred_feb_move = self.refund.cutoff_entry_ids.filtered(
            lambda move, move_date=date(2023, 2, 1): move.date == move_date
        )
        self.assertEqual(deferred_feb_move.journal_id, self.miscellaneous_journal)
        self.assertEqual(
            deferred_feb_move.ref,
            f"Advance revenue adjustment of {self.refund.name} (01 2023)",
        )
        self.assertAccountMoveLines(
            deferred_feb_move,
            [
                (
                    lambda ml: ml.debit > 0,
                    {"account_id": self.account_revenue, "credit": 0.0},
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case A" in ml.name,
                    {"debit": 1710.34},
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case B" in ml.name,
                    {"debit": 40.0},
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case C" in ml.name,
                    {"debit": 30.0},
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case D" in ml.name,
                    {"debit": 130.0},
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case F" in ml.name,
                    {"debit": 259.0},
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case I" in ml.name,
                    {"debit": 1016.39},
                ),
                (
                    lambda ml: ml.credit > 0,
                    {"account_id": self.account_cutoff, "debit": 0.0},
                ),
            ],
        )
        self.assertAlmostEqual(
            sum(
                deferred_feb_move.line_ids.filtered(lambda ml: ml.credit > 0).mapped(
                    "credit"
                )
            ),
            3185.73,
            2,
        )

        deferred_mar_move = self.refund.cutoff_entry_ids.filtered(
            lambda move, move_date=date(2023, 3, 1): move.date == move_date
        )
        self.assertEqual(deferred_mar_move.journal_id, self.miscellaneous_journal)
        self.assertEqual(
            deferred_mar_move.ref,
            f"Advance revenue adjustment of {self.refund.name} (01 2023)",
        )
        self.assertAccountMoveLines(
            deferred_mar_move,
            [
                (
                    lambda ml: ml.debit > 0,
                    {"account_id": self.account_revenue, "credit": 0.0},
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case A" in ml.name,
                    {"debit": 1710.34},
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case B" in ml.name,
                    {"debit": 40.0},
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case C" in ml.name,
                    {"debit": 30.0},
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case I" in ml.name,
                    {"debit": 491.80},
                ),
                (
                    lambda ml: ml.credit > 0,
                    {"account_id": self.account_cutoff, "debit": 0.0},
                ),
            ],
        )
        self.assertAlmostEqual(
            sum(
                deferred_mar_move.line_ids.filtered(lambda ml: ml.debit > 0).mapped(
                    "debit"
                )
            ),
            2272.14,
            2,
        )

        deferred_may_move = self.refund.cutoff_entry_ids.filtered(
            lambda move, move_date=date(2023, 5, 1): move.date == move_date
        )
        self.assertEqual(deferred_may_move.journal_id, self.miscellaneous_journal)
        self.assertEqual(
            deferred_may_move.ref,
            f"Advance revenue adjustment of {self.refund.name} (01 2023)",
        )
        self.assertAccountMoveLines(
            deferred_may_move,
            [
                (
                    lambda ml: ml.debit > 0,
                    {"account_id": self.account_revenue, "credit": 0.0},
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case G" in ml.name,
                    {"debit": 255.00},
                ),
                (
                    lambda ml: ml.credit > 0,
                    {"account_id": self.account_cutoff, "debit": 0.0},
                ),
            ],
        )
        self.assertAlmostEqual(
            sum(
                deferred_may_move.line_ids.filtered(lambda ml: ml.credit > 0).mapped(
                    "credit"
                )
            ),
            255.0,
            2,
        )
