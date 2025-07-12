from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    start_date = fields.Date(string="Start Date", help="Start of the period the entry belongs to")
    end_date = fields.Date(string="End Date", help="End of the period the entry belongs to")

    @api.constrains('start_date', 'end_date')
    def _check_cutoff_dates(self):
        """Ensure that start_date is not after end_date"""
        for line in self:
            if line.start_date and line.end_date and line.start_date > line.end_date:
                raise ValidationError("Start Date cannot be after End Date.")
