# Copyright 2026 Lorenzo Battistini
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    start_end_dates_from_bill_date = fields.Boolean(
        related="company_id.start_end_dates_from_bill_date", readonly=False
    )
    start_end_dates_from_invoice_date = fields.Boolean(
        related="company_id.start_end_dates_from_invoice_date", readonly=False
    )
