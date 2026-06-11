# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError

from odoo.addons.account_cutoff_base.post_install import company_country_cutoff_setup

from .common import AccountCutoffCommon


class TestAccountCutoff(AccountCutoffCommon):
    def test_post_install_country_cutoff_setup(self):
        self.env["account.account"].create(
            {
                "name": "Test Expense 2",
                "code": "408101",
                "account_type": "expense",
            }
        )
        self.company.account_fiscal_country_id = self.env["res.country"].search(
            [("code", "=", "FR")], limit=1
        )
        company_country_cutoff_setup(self.env)
        self.company._country_cutoff_setup()
        self.assertTrue(self.company.accrual_taxes)

    def test_post_install_country_cutoff_setup_no_account_found_and_multiple(self):
        country_fr = self.env["res.country"].search([("code", "=", "FR")], limit=1)
        # We temporarily change country code to something without accounts
        country_be = self.env["res.country"].search([("code", "=", "BE")], limit=1)
        self.company.account_fiscal_country_id = country_be

        self.env["account.account"].create(
            {
                "name": "Test Multi 1",
                "code": "XYZ8881",
                "account_type": "expense",
            }
        )
        self.env["account.account"].create(
            {
                "name": "Test Multi 2",
                "code": "XYZ8882",
                "account_type": "expense",
            }
        )

        # We fake a configuration for BE to hit the "no account found",
        # "multiple accounts", and fallback branches
        mock_return = {
            "BE": {
                "accrued_revenue": "XYZ999",  # 0 accounts
                "accrued_expense": "XYZ888",  # > 1 accounts
                "accrual_taxes": "invalid_type",
                "random_key": "value",
            }
        }
        with patch.object(
            type(self.company), "_country2cutoff_setup", return_value=mock_return
        ):
            company_country_cutoff_setup(self.env)
            self.company._country_cutoff_setup()

        self.company.account_fiscal_country_id = country_fr

    def test_post_install_country_cutoff_setup_no_vals(self):
        country_fr = self.env["res.country"].search([("code", "=", "FR")], limit=1)
        # Country US is not in setup, should just exit gracefully
        country_us = self.env["res.country"].search([("code", "=", "US")], limit=1)
        self.company.account_fiscal_country_id = country_us
        company_country_cutoff_setup(self.env)

        # Now fake setup that returns empty dict for a country to test vals being empty
        with patch.object(
            type(self.company), "_country2cutoff_setup", return_value={"US": {}}
        ):
            company_country_cutoff_setup(self.env)
            self.company._country_cutoff_setup()

        self.company.account_fiscal_country_id = country_fr

    def test_compute_cutoff_date_when_fiscalyear_exists(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
            }
        )
        self.assertTrue(cutoff.cutoff_date)

    def test_compute_cutoff_date_no_date_from(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
            }
        )
        with patch(
            "odoo.addons.account_cutoff_base.models."
            "account_cutoff.date_utils.get_fiscal_year",
            return_value=(False, False),
        ):
            cutoff._compute_cutoff_date()
        self.assertFalse(cutoff.cutoff_date)

    def test_compute_cutoff_account_id_accrued_expense(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
            }
        )
        self.assertEqual(cutoff.cutoff_account_id, self.account_expense)

    def test_compute_cutoff_account_id_accrued_revenue(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_revenue",
            }
        )
        self.assertEqual(cutoff.cutoff_account_id, self.account_revenue)

    def test_compute_cutoff_account_id_prepaid_revenue(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "prepaid_revenue",
            }
        )
        self.assertEqual(cutoff.cutoff_account_id, self.account_prepaid_revenue)

    def test_compute_cutoff_account_id_prepaid_expense(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "prepaid_expense",
            }
        )
        self.assertEqual(cutoff.cutoff_account_id, self.account_prepaid_expense)

    def test_compute_cutoff_account_id_other(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
            }
        )
        cutoff.cutoff_type = False
        cutoff._compute_cutoff_account_id()
        self.assertFalse(cutoff.cutoff_account_id)

    def test_get_mapping_dict(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
            }
        )

        # Add another mapping to test filtering
        self.env["account.cutoff.mapping"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "all",
                "account_id": self.account_revenue.id,
                "cutoff_account_id": self.account_prepaid_revenue.id,
            }
        )

        # 1. No source_accounts provided: should return all mappings for this company
        mapping = cutoff._get_mapping_dict()
        self.assertIn(self.account_expense.id, mapping)
        self.assertIn(self.account_revenue.id, mapping)

        # 2. source_accounts provided: should return ONLY mappings for those accounts
        mapping_filtered = cutoff._get_mapping_dict(
            source_accounts=self.account_expense
        )
        self.assertIn(self.account_expense.id, mapping_filtered)
        self.assertNotIn(self.account_revenue.id, mapping_filtered)

    def test_compute_display_name_no_date(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
            }
        )
        cutoff.cutoff_date = False
        cutoff._compute_display_name()
        self.assertEqual(cutoff.display_name, "Accrued Expense")

    def test_create_move_raises_when_no_lines(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
            }
        )
        with self.assertRaisesRegex(UserError, "There are no lines on this Cut-off"):
            cutoff.create_move()

    def test_create_move_successfully_generates_journal_entry(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.account_expense.id,
                            "cutoff_account_id": self.account_expense.id,
                            "partner_id": self.partner.id,
                            "cutoff_amount": 100.0,
                            "analytic_distribution": {"1": 100},
                            "tax_line_ids": [
                                Command.create(
                                    {
                                        "tax_id": self.tax.id,
                                        "base": 100.0,
                                        "amount": 20.0,
                                        "sequence": 1,
                                        "cutoff_account_id": (
                                            self.account_tax_expense.id
                                        ),
                                        "cutoff_amount": 20.0,
                                    }
                                )
                            ],
                        }
                    )
                ],
            }
        )

        self.assertEqual(cutoff.total_cutoff_amount, 100.0)
        self.assertIn("Accrued Expense", cutoff.display_name)

        action = cutoff.create_move()

        self.assertEqual(cutoff.state, "done")
        self.assertTrue(cutoff.move_id)
        self.assertEqual(action["res_id"], cutoff.move_id.id)
        self.assertEqual(
            cutoff.move_id.state, "posted"
        )  # because post_cutoff_move is True

        with self.assertRaisesRegex(
            UserError, "The Cut-off Journal Entry already exists"
        ):
            cutoff.create_move()

    def test_create_move_successfully_generates_negative_journal_entry(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.account_expense.id,
                            "cutoff_account_id": self.account_expense.id,
                            "partner_id": self.partner.id,
                            "cutoff_amount": -100.0,
                        }
                    )
                ],
            }
        )
        cutoff.create_move()
        self.assertEqual(cutoff.state, "done")

    def test_back2draft_deletes_move_and_resets_state(self):
        self.company.post_cutoff_move = False
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.account_expense.id,
                            "cutoff_account_id": self.account_expense.id,
                            "partner_id": self.partner.id,
                            "cutoff_amount": 100.0,
                        }
                    )
                ],
            }
        )
        cutoff.create_move()
        self.assertEqual(cutoff.state, "done")

        cutoff.back2draft()
        self.assertEqual(cutoff.state, "draft")
        self.assertFalse(cutoff.move_id)

    def test_back2draft_no_move(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
            }
        )
        cutoff.back2draft()
        self.assertEqual(cutoff.state, "draft")

    def test_get_lines_raises_when_no_cutoff_date(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
            }
        )
        cutoff.cutoff_date = False
        with self.assertRaisesRegex(UserError, "Cutoff date is not set"):
            cutoff.get_lines()

    def test_get_lines_clears_existing_lines(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.account_expense.id,
                            "cutoff_account_id": self.account_expense.id,
                            "partner_id": self.partner.id,
                            "cutoff_amount": 100.0,
                        }
                    )
                ],
            }
        )
        cutoff.get_lines()
        self.assertFalse(cutoff.line_ids)

    def test_unlink_raises_when_state_is_done(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.account_expense.id,
                            "cutoff_account_id": (self.account_expense.id),
                            "partner_id": self.partner.id,
                            "cutoff_amount": 100.0,
                        }
                    )
                ],
            }
        )
        cutoff.create_move()
        with self.assertRaisesRegex(UserError, "You cannot delete"):
            cutoff.unlink()

    def test_unlink_draft(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
            }
        )
        cutoff.unlink()
        self.assertFalse(cutoff.exists())

    def test_button_line_list_returns_action(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
            }
        )
        action = cutoff.button_line_list()
        self.assertEqual(action["domain"], [("parent_id", "=", cutoff.id)])

    def test_get_mapping_dict_returns_mapped_accounts(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
            }
        )
        mapping = cutoff._get_mapping_dict()
        self.assertEqual(
            mapping[self.account_expense.id], self.account_prepaid_expense.id
        )

    def test_prepare_tax_lines_creates_valid_commands(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
            }
        )
        tax_compute_all_res = {
            "taxes": [
                {
                    "id": self.tax.id,
                    "amount": 20.0,
                    "base": 100.0,
                    "sequence": 1,
                },
                {
                    "id": self.tax.id,
                    "amount": 0.0,
                    "base": 100.0,
                    "sequence": 1,
                },
            ]
        }
        res = cutoff._prepare_tax_lines(tax_compute_all_res, self.company.currency_id)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][2]["cutoff_amount"], 20.0)

    def test_prepare_tax_lines_raises_when_no_accrual_account(self):
        tax_without_accrual = self.env["account.tax"].create(
            {
                "name": "Tax Without Accrual",
                "amount": 10.0,
                "tax_group_id": self.tax_group.id,
            }
        )

        self.company.default_accrued_expense_tax_account_id = False

        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
            }
        )
        tax_compute_all_res = {
            "taxes": [
                {
                    "id": tax_without_accrual.id,
                    "amount": 10.0,
                    "base": 100.0,
                    "sequence": 1,
                }
            ]
        }
        with self.assertRaisesRegex(UserError, "Missing 'Accrued Expense Tax Account'"):
            cutoff._prepare_tax_lines(tax_compute_all_res, self.company.currency_id)

    def test_prepare_tax_lines_raises_when_no_accrual_account_revenue(self):
        tax_without_accrual = self.env["account.tax"].create(
            {
                "name": "Tax Without Accrual",
                "amount": 10.0,
                "tax_group_id": self.tax_group.id,
            }
        )

        self.company.default_accrued_revenue_tax_account_id = False

        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_revenue",
            }
        )
        tax_compute_all_res = {
            "taxes": [
                {
                    "id": tax_without_accrual.id,
                    "amount": 10.0,
                    "base": 100.0,
                    "sequence": 1,
                }
            ]
        }
        with self.assertRaisesRegex(UserError, "Missing 'Accrued Revenue Tax Account'"):
            cutoff._prepare_tax_lines(tax_compute_all_res, self.company.currency_id)

    def test_prepare_tax_lines_raises_when_prepaid(self):
        tax_without_accrual = self.env["account.tax"].create(
            {
                "name": "Tax Without Accrual",
                "amount": 10.0,
                "tax_group_id": self.tax_group.id,
            }
        )

        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "prepaid_expense",
            }
        )
        tax_compute_all_res = {
            "taxes": [
                {
                    "id": tax_without_accrual.id,
                    "amount": 10.0,
                    "base": 100.0,
                    "sequence": 1,
                }
            ]
        }
        with self.assertRaisesRegex(UserError, "Missing ''"):
            cutoff._prepare_tax_lines(tax_compute_all_res, self.company.currency_id)

    def test_selection_cutoff_type(self):
        cutoff = self.env["account.cutoff"].create(
            {
                "company_id": self.company.id,
                "cutoff_type": "accrued_expense",
            }
        )
        selection = cutoff._selection_cutoff_type()
        self.assertIn(("accrued_expense", "Accrued Expense"), selection)
