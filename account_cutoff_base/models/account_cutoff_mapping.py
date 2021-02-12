# Copyright 2013-2021 Akretion (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountCutoffMapping(models.Model):
    _name = "account.cutoff.mapping"
    _description = "Account Cut-off Mapping"
    _check_company_auto = True
    _rec_name = "account_id"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    account_id = fields.Many2one(
        "account.account",
        string="Regular Account",
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        required=True,
        check_company=True,
    )
    cutoff_account_id = fields.Many2one(
        "account.account",
        string="Cut-off Account",
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        required=True,
        check_company=True,
    )
    cutoff_type = fields.Selection(
        [
            ("all", "All Cut-off Types"),
            ("accrued_revenue", "Accrued Revenue"),
            ("accrued_expense", "Accrued Expense"),
            ("prepaid_revenue", "Prepaid Revenue"),
            ("prepaid_expense", "Prepaid Expense"),
        ],
        string="Cut-off Type",
        required=True,
        default="all",
    )
