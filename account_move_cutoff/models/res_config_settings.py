# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    revenue_cutoff_journal_id = fields.Many2one(
        related="company_id.revenue_cutoff_journal_id",
        readonly=False,
        string="Revenue cut-off journal",
    )
    expense_cutoff_journal_id = fields.Many2one(
        related="company_id.expense_cutoff_journal_id",
        readonly=False,
        string="Expense cut-off journal",
    )
