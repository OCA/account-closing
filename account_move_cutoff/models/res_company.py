# Copyright 2023 Foodles (http://www.foodles.co).
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    revenue_cutoff_journal_id = fields.Many2one(
        "account.journal",
        string="Cut-off Revenue Journal",
        check_company=True,
    )
    expense_cutoff_journal_id = fields.Many2one(
        "account.journal",
        string="Cut-off Expense Journal",
        check_company=True,
    )
