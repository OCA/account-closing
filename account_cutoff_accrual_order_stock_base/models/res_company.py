# Copyright 2026 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    default_stock_prepaid_revenue_account_id = fields.Many2one(
        "account.account",
        string="Default Account for Prepaid Revenue on Sales Order",
        help="Account for goods invoiced not yet delivered",
        check_company=True,
    )
    default_stock_prepaid_expense_account_id = fields.Many2one(
        "account.account",
        string="Default Account for Prepaid Expense on Purchase Order",
        help="Account for goods invoiced not yet received",
        check_company=True,
    )
