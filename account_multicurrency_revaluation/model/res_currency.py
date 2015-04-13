# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2012 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time

from openerp import models, api, _
from openerp.exceptions import Warning


class ResCurrency(models.Model):

    _inherit = 'res.currency'

    @api.model
    def _get_conversion_rate(self, from_currency, to_currency):
        context = self.env.context
        if 'revaluation' in context:
            rate = from_currency.rate
            if rate == 0.0:
                date = context.get('date', time.strftime('%Y-%m-%d'))
                raise Warning(
                    _('No rate found '
                      'for the currency: %s '
                      'at the date: %s') %
                    (from_currency.symbol, date)
                )
            return 1.0 / rate

        else:
            return super(ResCurrency, self)._get_conversion_rate(
                from_currency, to_currency)
