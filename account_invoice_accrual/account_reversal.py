# -*- coding: utf-8 -*-
##############################################################################
#
#     Authors: Adrien Peiffer
#    Copyright (c) 2015 Acsone SA/NV (http://www.acsone.eu)
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

from openerp.osv import orm


class account_move(orm.Model):
    _inherit = "account.move"

    def _move_reversal(self, cr, uid, move, reversal_date,
                       reversal_period_id=False, reversal_journal_id=False,
                       move_prefix=False, move_line_prefix=False,
                       context=None):
        """ Override _move_reversal to allow to set reversal period with
            the same period than the invoice's move in case of invoice's
            validation """
        if context.get('from_invoice_validate'):
            invoice_obj = self.pool['account.invoice']
            invoice_id = invoice_obj\
                .search(cr, uid, [('accrual_move_id', '=', move.id)])[0]
            invoice = invoice_obj.browse(cr, uid, [invoice_id],
                                         context=context)[0]
            period = invoice.move_id.period_id
            reversal_period_id = period.id
            reversal_date = period.date_start
        return super(account_move, self).\
            _move_reversal(cr, uid, move, reversal_date,
                           reversal_period_id=reversal_period_id,
                           reversal_journal_id=reversal_journal_id,
                           move_prefix=move_prefix,
                           move_line_prefix=move_line_prefix,
                           context=context)
