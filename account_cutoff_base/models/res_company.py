# Copyright 2013-2021 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2017-2021 ACSONE SA/NV
# Copyright 2018-2021 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    default_cutoff_journal_id = fields.Many2one(
        "account.journal",
        string="Default Cut-off Journal",
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
        check_company=True,
    )
    default_cutoff_move_partner = fields.Boolean(
        string="Partner on Move Line by Default"
    )
    accrual_taxes = fields.Boolean(string="Accrual On Taxes", default=True)
    default_accrued_revenue_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Default Account for Accrued Revenues",
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
    )
    default_accrued_expense_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Default Account for Accrued Expenses",
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
    )
    default_prepaid_revenue_account_id = fields.Many2one(
        "account.account",
        string="Default Account for Prepaid Revenue",
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
    )
    default_prepaid_expense_account_id = fields.Many2one(
        "account.account",
        string="Default Account for Prepaid Expense",
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
    )
