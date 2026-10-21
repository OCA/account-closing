# Copyright 2026 Lorenzo Battistini
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    dft_accrued_revenue_spanning_account_id = fields.Many2one(
        related="company_id.default_accrued_revenue_spanning_account_id",
        readonly=False,
        domain="[('deprecated', '=', False), ('company_ids', 'in', company_id)]",
    )
    dft_accrued_expense_spanning_account_id = fields.Many2one(
        related="company_id.default_accrued_expense_spanning_account_id",
        readonly=False,
        domain="[('deprecated', '=', False), ('company_ids', 'in', company_id)]",
    )
