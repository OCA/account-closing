# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import SavepointCase


class TestAccountCutoff(SavepointCase):
    def test_default_cutoff_account_id(self):
        account_id = self.env["account.cutoff"]._default_cutoff_account_id()
        self.assertEqual(account_id, False)

        company = self.env.company
        random_account = self.env["account.account"].search(
            [("company_id", "=", company.id)], limit=1
        )
        if random_account:
            company.default_accrued_expense_account_id = random_account.id
            company.default_accrued_revenue_account_id = random_account.id

            account_id = (
                self.env["account.cutoff"]
                .with_context(default_cutoff_type="accrued_expense")
                ._default_cutoff_account_id()
            )
            self.assertEqual(
                account_id,
                random_account.id,
                "The account must be equals to %s" % random_account.id,
            )
            account_id = (
                self.env["account.cutoff"]
                .with_context(default_cutoff_type="accrued_revenue")
                ._default_cutoff_account_id()
            )
            self.assertEqual(
                account_id,
                random_account.id,
                "The account must be equals to %s" % random_account.id,
            )
