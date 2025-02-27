# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestAccountCutoff(TransactionCase):
    def test_compute_cutoff_account_id(self):
        company = self.env.company
        random_account = self.env["account.account"].search(
            [("company_ids", "in", company.id)], limit=1
        )
        if random_account:
            company.default_accrued_expense_account_id = random_account.id
            company.default_accrued_revenue_account_id = random_account.id

            cutoff = self.env["account.cutoff"].create(
                {
                    "company_id": company.id,
                    "cutoff_type": "accrued_expense",
                }
            )
            self.assertEqual(
                cutoff.cutoff_account_id.id,
                random_account.id,
                f"The account must be equals to {random_account.id}",
            )
            cutoff2 = self.env["account.cutoff"].create(
                {
                    "company_id": company.id,
                    "cutoff_type": "accrued_revenue",
                }
            )
            self.assertEqual(
                cutoff2.cutoff_account_id.id,
                random_account.id,
                f"The account must be equals to {random_account.id}",
            )
