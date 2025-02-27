# Copyright 2013-2021 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2017-2021 ACSONE SA/NV
# Copyright 2018-2021 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging

from odoo import api, fields, models

logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    default_cutoff_journal_id = fields.Many2one(
        "account.journal",
        string="Default Cut-off Journal",
        check_company=True,
    )
    default_cutoff_move_partner = fields.Boolean(
        string="Partner on Journal Items by Default"
    )
    accrual_taxes = fields.Boolean(string="Accrual On Taxes", default=True)
    post_cutoff_move = fields.Boolean(string="Post Cut-off Journal Entry")
    default_accrued_revenue_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Default Account for Accrued Revenues",
        check_company=True,
    )
    default_accrued_expense_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Default Account for Accrued Expenses",
        check_company=True,
    )
    default_accrued_revenue_tax_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Default Tax Account for Accrued Revenue",
        check_company=True,
    )
    default_accrued_expense_tax_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Default Tax Account for Accrued Expense",
        check_company=True,
    )
    default_prepaid_revenue_account_id = fields.Many2one(
        "account.account",
        string="Default Account for Prepaid Revenue",
        check_company=True,
    )
    default_prepaid_expense_account_id = fields.Many2one(
        "account.account",
        string="Default Account for Prepaid Expense",
        check_company=True,
    )

    def _country_cutoff_setup(self):
        """Called by post install script"""
        self.ensure_one()
        assert self.account_fiscal_country_id
        country2setup = self._country2cutoff_setup()
        country_code = self.account_fiscal_country_id.code.upper()
        if country_code in country2setup:
            logger.info(
                "Autoconfiguring cutoff accounts on company %s fiscal country %s",
                self.display_name,
                country_code,
            )
            vals = {}
            for setup_entry, setup_value in country2setup[country_code].items():
                self._update_cutoff_vals(setup_entry, setup_value, vals)
            if vals:
                self.write(vals)

    def _update_cutoff_vals(self, setup_entry, setup_value, vals):
        self.ensure_one()
        if (
            setup_entry
            in [
                "accrued_revenue",
                "accrued_expense",
                "accrued_revenue_tax",
                "accrued_expense_tax",
                "prepaid_revenue",
                "prepaid_expense",
            ]
            and setup_value
            and isinstance(setup_value, str)
        ):
            field_name = f"default_{setup_entry}_account_id"
            accounts = (
                self.env["account.account"]
                .with_company(self.id)
                .search(
                    [
                        ("deprecated", "=", False),
                        ("company_ids", "in", self.id),
                        ("code", "=like", f"{setup_value}%"),
                    ],
                )
            )
            if len(accounts) == 1:
                logger.info(
                    "Account %s selected for %s", accounts.display_name, field_name
                )
                vals[field_name] = accounts.id
            elif len(accounts) > 1:
                logger.warning(
                    "%d accounts with prefix %s. Selected first account %s for %s",
                    len(accounts),
                    setup_value,
                    accounts[0].display_name,
                    field_name,
                )
                vals[field_name] = accounts[0].id
            else:
                logger.info(
                    "No account found with prefix %s for %s", setup_value, field_name
                )
        elif setup_entry == "accrual_taxes" and isinstance(setup_value, bool):
            vals["accrual_taxes"] = setup_value

    @api.model
    def _country2cutoff_setup(self):
        # You can contribute the cutoff setup for your country here
        res = {
            "FR": {
                "accrual_taxes": True,
                "accrued_revenue": "4181",
                "accrued_expense": "4081",
                "accrued_revenue_tax": "44587",
                "accrued_expense_tax": "44586",
                "prepaid_revenue": "487",
                "prepaid_expense": "486",
            }
        }
        return res
