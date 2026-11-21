# Copyright 2026 Lorenzo Battistini
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    default_accrued_revenue_spanning_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Default Account for Spanning Accrued Revenues",
        check_company=True,
    )
    default_accrued_expense_spanning_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Default Account for Spanning Accrued Expenses",
        check_company=True,
    )
