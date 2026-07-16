# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class AccountCutoffCommon(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.account_expense = cls.company_data["default_account_expense"]
        cls.account_revenue = cls.company_data["default_account_revenue"]

        cls.account_prepaid_expense = cls.env["account.account"].create(
            {
                "name": "Prepaid Expense",
                "code": "486000",
                "account_type": "asset_current",
            }
        )
        cls.account_prepaid_revenue = cls.env["account.account"].create(
            {
                "name": "Prepaid Revenue",
                "code": "487000",
                "account_type": "liability_current",
            }
        )
        cls.account_tax_expense = cls.env["account.account"].create(
            {
                "name": "Tax Expense",
                "code": "445860",
                "account_type": "asset_current",
            }
        )
        cls.account_tax_revenue = cls.env["account.account"].create(
            {
                "name": "Tax Revenue",
                "code": "445870",
                "account_type": "liability_current",
            }
        )

        cls.cutoff_journal = cls.company_data["default_journal_misc"]

        cls.company.write(
            {
                "default_accrued_expense_account_id": cls.account_expense.id,
                "default_accrued_revenue_account_id": cls.account_revenue.id,
                "default_prepaid_expense_account_id": cls.account_prepaid_expense.id,
                "default_prepaid_revenue_account_id": cls.account_prepaid_revenue.id,
                "default_accrued_expense_tax_account_id": cls.account_tax_expense.id,
                "default_accrued_revenue_tax_account_id": cls.account_tax_revenue.id,
                "default_cutoff_journal_id": cls.cutoff_journal.id,
                "default_cutoff_move_partner": True,
                "post_cutoff_move": True,
            }
        )

        cls.partner = cls.partner_a

        cls.tax_group = cls.env["account.tax.group"].create({"name": "Test Tax Group"})
        cls.tax = cls.env["account.tax"].create(
            {
                "name": "Test Tax",
                "amount": 20.0,
                "tax_group_id": cls.tax_group.id,
                "account_accrued_expense_id": cls.account_tax_expense.id,
                "account_accrued_revenue_id": cls.account_tax_revenue.id,
            }
        )

        cls.env["account.cutoff.mapping"].create(
            {
                "company_id": cls.company.id,
                "cutoff_type": "all",
                "account_id": cls.account_expense.id,
                "cutoff_account_id": cls.account_prepaid_expense.id,
            }
        )
