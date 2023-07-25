# Copyright 2023 Foodles (https://www.foodles.co/)
# @author: Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import date

from freezegun import freeze_time

from odoo.tests import tagged

from .common import CommonAccountInvoiceCutoffCase


@tagged("-at_install", "post_install")
class TestInvoiceCutoff(CommonAccountInvoiceCutoffCase):
    def test_ensure_invoice_without_start_end_date_are_postable(self):
        self.invoice.line_ids.product_id.must_have_dates = False
        self.invoice.line_ids.write({"start_date": False, "end_date": False})
        self.invoice.action_post()
        self.assertEqual(self.invoice.state, "posted")

    def test_get_deferred_periods_only_past_services(self):
        self.invoice.date = date(2024, 1, 1)
        self.assertEqual(
            self.invoice._get_deferred_periods(
                self.invoice.line_ids.filtered(lambda line: line.end_date)
            ),
            [date(2024, 1, 1)],
        )

    def test_account_invoice_cutoff_all_pasted_periods(self):
        self.invoice.date = self.invoice.invoice_date = date(2023, 12, 1)
        with freeze_time("2023-12-01"):
            self.invoice.action_post()
        self.assertEqual(self.invoice.cutoff_move_count, 0)

    def test_account_invoice_cutoff_equals(self):
        self.invoice.line_ids.cutoff_method = "equal"
        with freeze_time("2023-01-15"):
            self.invoice.action_post()
        self.assertEqual(self.invoice.cutoff_move_count, 4)

    def test_avoid_duplicated_entries(self):
        with freeze_time("2023-01-15"):
            self.invoice.action_post()
            self.invoice.button_draft()
            self.assertEqual(self.invoice.cutoff_move_count, 0)
            self.invoice.action_post()
        self.assertEqual(self.invoice.cutoff_move_count, 4)

    def test_action_view_deferred_entries(self):
        with freeze_time("2023-01-15"):
            self.invoice.action_post()
        action = self.invoice.action_view_deferred_entries()
        self.assertEqual(action["domain"][0][2], self.invoice.cutoff_entry_ids.ids)

    def test_account_invoice_cutoff_monthly_factor_prorata(self):
        self.invoice.line_ids.cutoff_method = "monthly_prorata_temporis"

        with freeze_time("2023-01-15"):
            self.invoice.action_post()
        self.assertEqual(self.invoice.cutoff_move_count, 4)

        cutoff_move = self.invoice.cutoff_entry_ids.filtered(
            lambda move, move_date=date(2023, 1, 15): move.date == move_date
        )

        self.assertEqual(cutoff_move.journal_id, self.miscellaneous_journal)
        self.assertEqual(
            cutoff_move.ref,
            f"Advance revenue recognition of {self.invoice.name} (01 2023)",
        )
        self.assertAccountMoveLines(
            cutoff_move,
            [
                (
                    lambda ml: ml.debit > 0,
                    {
                        "account_id": self.account_revenue,
                        "credit": 0.0,
                        "cutoff_source_move_id": self.invoice,
                        "partner_id": self.env.ref("base.res_partner_2"),
                    },
                ),
                (
                    lambda ml: ml.credit > 0,
                    {
                        "account_id": self.account_cutoff,
                        "reconciled": True,
                        "debit": 0.0,
                        "cutoff_source_move_id": self.invoice,
                        "partner_id": self.env.ref("base.res_partner_2"),
                        "analytic_account_id": self.env[
                            "account.analytic.account"
                        ].browse(),
                    },
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case A" in ml.name,
                    {
                        "debit": 3420.68,
                        "cutoff_source_id": self.invoice.line_ids.filtered(
                            lambda ml, account=self.account_revenue: ml.account_id
                            == account
                            and "Case A" in ml.name
                        ),
                        "analytic_account_id": self.analytic,
                        "start_date": date(2023, 2, 1),
                        "end_date": date(2023, 3, 31),
                    },
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case B" in ml.name,
                    {
                        "debit": 80.0,
                        "cutoff_source_id": self.invoice.line_ids.filtered(
                            lambda ml, account=self.account_revenue: ml.account_id
                            == account
                            and "Case B" in ml.name
                        ),
                        "analytic_account_id": self.env[
                            "account.analytic.account"
                        ].browse(),
                        "start_date": date(2023, 2, 1),
                        "end_date": date(2023, 3, 31),
                    },
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case C" in ml.name,
                    {
                        "debit": 60.0,
                        "cutoff_source_id": self.invoice.line_ids.filtered(
                            lambda ml, account=self.account_revenue: ml.account_id
                            == account
                            and "Case C" in ml.name
                        ),
                        "analytic_account_id": self.env[
                            "account.analytic.account"
                        ].browse(),
                        "start_date": date(2023, 2, 1),
                        "end_date": date(2023, 3, 31),
                    },
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case D" in ml.name,
                    {
                        "debit": 130.0,
                        "cutoff_source_id": self.invoice.line_ids.filtered(
                            lambda ml, account=self.account_revenue: ml.account_id
                            == account
                            and "Case D" in ml.name
                        ),
                        "analytic_account_id": self.env[
                            "account.analytic.account"
                        ].browse(),
                        "start_date": date(2023, 2, 1),
                        "end_date": date(2023, 2, 28),
                    },
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case F" in ml.name,
                    {
                        "debit": 259.0,
                        "cutoff_source_id": self.invoice.line_ids.filtered(
                            lambda ml, account=self.account_revenue: ml.account_id
                            == account
                            and "Case F" in ml.name
                        ),
                        "analytic_account_id": self.env[
                            "account.analytic.account"
                        ].browse(),
                        "start_date": date(2023, 2, 1),
                        "end_date": date(2023, 2, 28),
                    },
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case G" in ml.name,
                    {
                        "debit": 255.0,
                        "cutoff_source_id": self.invoice.line_ids.filtered(
                            lambda ml, account=self.account_revenue: ml.account_id
                            == account
                            and "Case G" in ml.name
                        ),
                        "analytic_account_id": self.env[
                            "account.analytic.account"
                        ].browse(),
                        "start_date": date(2023, 5, 1),
                        "end_date": date(2023, 5, 31),
                    },
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case I" in ml.name,
                    {
                        "debit": 1508.19,
                        "cutoff_source_id": self.invoice.line_ids.filtered(
                            lambda ml, account=self.account_revenue: ml.account_id
                            == account
                            and "Case I" in ml.name
                        ),
                        "analytic_account_id": self.env[
                            "account.analytic.account"
                        ].browse(),
                        "start_date": date(2023, 2, 1),
                        "end_date": date(2023, 3, 15),
                    },
                ),
            ],
        )
        self.assertAlmostEqual(
            sum(
                cutoff_move.line_ids.filtered(lambda ml: ml.credit > 0).mapped("credit")
            ),
            5712.87,
            2,
        )

        deferred_feb_move = self.invoice.cutoff_entry_ids.filtered(
            lambda move, move_date=date(2023, 2, 1): move.date == move_date
        )
        self.assertEqual(deferred_feb_move.journal_id, self.miscellaneous_journal)
        self.assertEqual(
            deferred_feb_move.ref,
            f"Advance revenue adjustment of {self.invoice.name} (01 2023)",
        )
        self.assertAccountMoveLines(
            deferred_feb_move,
            [
                (
                    lambda ml: ml.credit > 0,
                    {
                        "account_id": self.account_revenue,
                        "debit": 0.0,
                        "cutoff_source_move_id": self.invoice,
                        "partner_id": self.env.ref("base.res_partner_2"),
                    },
                ),
                (
                    lambda ml: ml.debit > 0,
                    {
                        "account_id": self.account_cutoff,
                        "reconciled": True,
                        "credit": 0.0,
                        "cutoff_source_move_id": self.invoice,
                        "partner_id": self.env.ref("base.res_partner_2"),
                        "analytic_account_id": self.env[
                            "account.analytic.account"
                        ].browse(),
                    },
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case A" in ml.name,
                    {
                        "credit": 1710.34,
                        "cutoff_source_id": self.invoice.line_ids.filtered(
                            lambda ml, account=self.account_revenue: ml.account_id
                            == account
                            and "Case A" in ml.name
                        ),
                        "analytic_account_id": self.analytic,
                        "start_date": date(2023, 2, 1),
                        "end_date": date(2023, 2, 28),
                    },
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case B" in ml.name,
                    {
                        "credit": 40.0,
                        "cutoff_source_id": self.invoice.line_ids.filtered(
                            lambda ml, account=self.account_revenue: ml.account_id
                            == account
                            and "Case B" in ml.name
                        ),
                        "analytic_account_id": self.env[
                            "account.analytic.account"
                        ].browse(),
                        "start_date": date(2023, 2, 1),
                        "end_date": date(2023, 2, 28),
                    },
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case C" in ml.name,
                    {
                        "credit": 30.0,
                        "cutoff_source_id": self.invoice.line_ids.filtered(
                            lambda ml, account=self.account_revenue: ml.account_id
                            == account
                            and "Case C" in ml.name
                        ),
                        "analytic_account_id": self.env[
                            "account.analytic.account"
                        ].browse(),
                        "start_date": date(2023, 2, 1),
                        "end_date": date(2023, 2, 28),
                    },
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case D" in ml.name,
                    {
                        "credit": 130.0,
                        "cutoff_source_id": self.invoice.line_ids.filtered(
                            lambda ml, account=self.account_revenue: ml.account_id
                            == account
                            and "Case D" in ml.name
                        ),
                        "analytic_account_id": self.env[
                            "account.analytic.account"
                        ].browse(),
                        "start_date": date(2023, 2, 1),
                        "end_date": date(2023, 2, 28),
                    },
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case F" in ml.name,
                    {
                        "credit": 259.0,
                        "cutoff_source_id": self.invoice.line_ids.filtered(
                            lambda ml, account=self.account_revenue: ml.account_id
                            == account
                            and "Case F" in ml.name
                        ),
                        "analytic_account_id": self.env[
                            "account.analytic.account"
                        ].browse(),
                        "start_date": date(2023, 2, 1),
                        "end_date": date(2023, 2, 28),
                    },
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case I" in ml.name,
                    {
                        "credit": 1016.39,
                        "cutoff_source_id": self.invoice.line_ids.filtered(
                            lambda ml, account=self.account_revenue: ml.account_id
                            == account
                            and "Case I" in ml.name
                        ),
                        "analytic_account_id": self.env[
                            "account.analytic.account"
                        ].browse(),
                        "start_date": date(2023, 2, 1),
                        "end_date": date(2023, 2, 28),
                    },
                ),
            ],
        )
        self.assertAlmostEqual(
            sum(
                deferred_feb_move.line_ids.filtered(lambda ml: ml.debit > 0).mapped(
                    "debit"
                )
            ),
            3185.73,
            2,
        )

        deferred_mar_move = self.invoice.cutoff_entry_ids.filtered(
            lambda move, move_date=date(2023, 3, 1): move.date == move_date
        )
        self.assertEqual(deferred_mar_move.journal_id, self.miscellaneous_journal)
        self.assertEqual(
            deferred_mar_move.ref,
            f"Advance revenue adjustment of {self.invoice.name} (01 2023)",
        )
        self.assertAccountMoveLines(
            deferred_mar_move,
            [
                (
                    lambda ml: ml.credit > 0,
                    {
                        "account_id": self.account_revenue,
                        "debit": 0.0,
                        "cutoff_source_move_id": self.invoice,
                        "partner_id": self.env.ref("base.res_partner_2"),
                    },
                ),
                (
                    lambda ml: ml.debit > 0,
                    {
                        "account_id": self.account_cutoff,
                        "reconciled": True,
                        "credit": 0.0,
                        "cutoff_source_move_id": self.invoice,
                        "partner_id": self.env.ref("base.res_partner_2"),
                        "analytic_account_id": self.env[
                            "account.analytic.account"
                        ].browse(),
                    },
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case A" in ml.name,
                    {
                        "credit": 1710.34,
                        "cutoff_source_id": self.invoice.line_ids.filtered(
                            lambda ml, account=self.account_revenue: ml.account_id
                            == account
                            and "Case A" in ml.name
                        ),
                        "analytic_account_id": self.analytic,
                        "start_date": date(2023, 3, 1),
                        "end_date": date(2023, 3, 31),
                    },
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case B" in ml.name,
                    {
                        "credit": 40.0,
                        "cutoff_source_id": self.invoice.line_ids.filtered(
                            lambda ml, account=self.account_revenue: ml.account_id
                            == account
                            and "Case B" in ml.name
                        ),
                        "analytic_account_id": self.env[
                            "account.analytic.account"
                        ].browse(),
                        "start_date": date(2023, 3, 1),
                        "end_date": date(2023, 3, 31),
                    },
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case C" in ml.name,
                    {
                        "credit": 30.0,
                        "cutoff_source_id": self.invoice.line_ids.filtered(
                            lambda ml, account=self.account_revenue: ml.account_id
                            == account
                            and "Case C" in ml.name
                        ),
                        "analytic_account_id": self.env[
                            "account.analytic.account"
                        ].browse(),
                        "start_date": date(2023, 3, 1),
                        "end_date": date(2023, 3, 31),
                    },
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case I" in ml.name,
                    {
                        "credit": 491.80,
                        "cutoff_source_id": self.invoice.line_ids.filtered(
                            lambda ml, account=self.account_revenue: ml.account_id
                            == account
                            and "Case I" in ml.name
                        ),
                        "analytic_account_id": self.env[
                            "account.analytic.account"
                        ].browse(),
                        "start_date": date(2023, 3, 1),
                        "end_date": date(2023, 3, 15),
                    },
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

        deferred_may_move = self.invoice.cutoff_entry_ids.filtered(
            lambda move, move_date=date(2023, 5, 1): move.date == move_date
        )
        self.assertEqual(deferred_may_move.journal_id, self.miscellaneous_journal)
        self.assertEqual(
            deferred_may_move.ref,
            f"Advance revenue adjustment of {self.invoice.name} (01 2023)",
        )
        self.assertAccountMoveLines(
            deferred_may_move,
            [
                (
                    lambda ml: ml.credit > 0,
                    {
                        "account_id": self.account_revenue,
                        "debit": 0.0,
                        "cutoff_source_move_id": self.invoice,
                        "partner_id": self.env.ref("base.res_partner_2"),
                        "analytic_account_id": self.env[
                            "account.analytic.account"
                        ].browse(),
                    },
                ),
                (
                    lambda ml: ml.debit > 0,
                    {
                        "account_id": self.account_cutoff,
                        "reconciled": True,
                        "credit": 0.0,
                        "cutoff_source_move_id": self.invoice,
                        "partner_id": self.env.ref("base.res_partner_2"),
                        "analytic_account_id": self.env[
                            "account.analytic.account"
                        ].browse(),
                    },
                ),
                (
                    lambda ml, account=self.account_revenue: ml.account_id == account
                    and "Case G" in ml.name,
                    {
                        "credit": 255.00,
                        "cutoff_source_id": self.invoice.line_ids.filtered(
                            lambda ml, account=self.account_revenue: ml.account_id
                            == account
                            and "Case G" in ml.name
                        ),
                        "start_date": date(2023, 5, 1),
                        "end_date": date(2023, 5, 31),
                    },
                ),
            ],
        )
        self.assertAlmostEqual(
            sum(
                deferred_may_move.line_ids.filtered(lambda ml: ml.debit > 0).mapped(
                    "debit"
                )
            ),
            255.0,
            2,
        )
