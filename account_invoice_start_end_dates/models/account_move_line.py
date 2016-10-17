# -*- coding: utf-8 -*-
# © 2013-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    start_date = fields.Date('Start Date', index=True)
    end_date = fields.Date('End Date', index=True)

    @api.multi
    @api.constrains('start_date', 'end_date')
    def _check_start_end_dates(self):
        for moveline in self:
            if moveline.start_date and not moveline.end_date:
                raise ValidationError(
                    _("Missing End Date for move line with Name '%s'.")
                    % (moveline.name))
            if moveline.end_date and not moveline.start_date:
                raise ValidationError(
                    _("Missing Start Date for move line with Name '%s'.")
                    % (moveline.name))
            if moveline.end_date and moveline.start_date and \
                    moveline.start_date > moveline.end_date:
                raise ValidationError(_(
                    "Start Date should be before End Date for move line "
                    "with Name '%s'.")
                    % (moveline.name))
        # should we check that it's related to an expense / revenue ?
        # -> I don't think so
