# Copyright 2012-2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import time

from odoo import models, api, _
from odoo.exceptions import Warning as UserError


class ResCurrency(models.Model):

    _inherit = 'res.currency'

    @api.model
    def _get_conversion_rate(self, from_currency, to_currency):
        context = self.env.context
        if 'revaluation' in context:
            rate = from_currency.rate
            if rate == 0.0:
                date = context.get('date', time.strftime('%Y-%m-%d'))
                raise UserError(
                    _('No rate found '
                      'for the currency: %s '
                      'at the date: %s') %
                    (from_currency.symbol, date)
                )
            return 1.0 / rate

        else:
            return super()._get_conversion_rate(from_currency, to_currency)
