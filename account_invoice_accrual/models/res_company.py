# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):

    _inherit = "res.company"

    dft_accrual_revenue_journal_id = fields.Many2one(
        comodel_name="account.journal", string="Default Journal for Accrued Revenues"
    )
    dft_accrual_expense_journal_id = fields.Many2one(
        comodel_name="account.journal", string="Default Journal for Accrued Expenses"
    )
