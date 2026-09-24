# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestCutoffAccrualSubscription(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company
        cls.company.accrual_taxes = False
        cls.subscription = cls.env["account.cutoff.accrual.subscription"].create(
            {
                "name": "Electricity",
                "subscription_type": "expense",
                "partner_type": "none",
                "periodicity": "month",
                "start_date": "2025-12-01",
                "min_amount": 100,
                "account_id": cls.company_data["default_account_expense"].id,
            }
        )

    def _create_cutoff(self, accrual_scope):
        return self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_date": fields.Date.to_date("2025-12-31"),
                "cutoff_type": "accrued_expense",
                "accrual_scope": accrual_scope,
            }
        )

    def test_accrual_scope(self):
        """Subscriptions are provisioned on periods ending by the cut-off date"""
        cutoff_partial = self._create_cutoff("partial")
        cutoff_partial.get_lines()
        self.assertFalse(cutoff_partial.line_ids)

        # no expense recorded in December: the minimum amount is provisioned
        cutoff_full = self._create_cutoff("full")
        cutoff_full.get_lines()
        self.assertEqual(cutoff_full.line_ids.subscription_id, self.subscription)
        self.assertEqual(cutoff_full.total_cutoff_amount, -100)

        with self.assertRaises(ValidationError):
            self._create_cutoff("all")
