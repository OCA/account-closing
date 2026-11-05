# Copyright 2026 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    dft_stock_prepaid_revenue_account_id = fields.Many2one(
        related="company_id.default_stock_prepaid_revenue_account_id",
        readonly=False,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
    )
    dft_stock_prepaid_expense_account_id = fields.Many2one(
        related="company_id.default_stock_prepaid_expense_account_id",
        readonly=False,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
    )
