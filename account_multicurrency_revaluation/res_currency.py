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

from osv import osv
from tools.translate import _


class res_currency(osv.osv):

    _inherit = 'res.currency'

    def _get_conversion_rate(self, cr, uid, from_currency,
                             to_currency, context=None):
        if context is None:
            context = {}
        if 'revaluation' in context:
            currency = self.browse(cr, uid, from_currency.id, context=context)
            rate = currency.rate
            if rate == 0.0:
                date = context.get('date', time.strftime('%Y-%m-%d'))
                raise osv.except_osv(_('Error'),
                                     _('No rate found \n'
                                       'for the currency: %s \n'
                                       'at the date: %s') %
                                     (currency.symbol, date))
            return 1.0 / rate

        else:
            return super(res_currency, self)._get_conversion_rate(
                cr, uid, from_currency, to_currency, context=context)

res_currency()
