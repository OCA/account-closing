from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    apply_dates_all_lines = fields.Boolean(
        related="company_id.apply_dates_all_lines", readonly=False
    )
