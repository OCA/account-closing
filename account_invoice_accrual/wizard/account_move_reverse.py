# -*- coding: utf-8 -*-
#
#
#    Authors: Laetitia Gangloff
#    Copyright (c) 2014 Acsone SA/NV (http://www.acsone.eu)
#    All Rights Reserved
#
#    WARNING: This program as such is intended to be used by professional
#    programmers who take the whole responsibility of assessing all potential
#    consequences resulting from its eventual inadequacies and bugs.
#    End users who are looking for a ready-to-use solution with commercial
#    guarantees and support are strongly advised to contact a Free Software
#    Service Company.
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
#
from openerp.osv import orm
from openerp.tools.translate import _


import logging
_logger = logging.getLogger(__name__)


class account_move_reversal(orm.TransientModel):
    _inherit = "account.move.reverse"

    def _default_journal(self, cr, uid, context=None):
        if context is None:
            context = {}
        if context.get('active_model') and \
                context.get('active_ids') and \
                context['active_model'] == 'account.invoice':
            inv = self.pool.get('account.invoice').browse(
                cr, uid, context['active_ids'])[0]
            if inv.partner_id.property_journal_accrual:
                return inv.partner_id.property_journal_accrual.id
        return None

    _defaults = {
        'journal_id': _default_journal,
    }

    def action_reverse(self, cr, uid, ids, context=None):
        # get the id of the journal items to inverse
        if context is None:
            context = {}
        inv_obj = self.pool.get('account.invoice')
        invoice_ids = []
        if context.get('active_model') and \
                context.get('active_ids') and \
                context['active_model'] == 'account.invoice':
            invoices = inv_obj.browse(cr, uid, context['active_ids'])
            move_ids = []
            invoice_ids = context['active_ids']
            for inv in invoices:
                if inv.state in ('draft', 'proforma2') and inv.accrual_move_id:
                    move_ids.append(inv.accrual_move_id.id)
            if move_ids:
                context['active_ids'] = move_ids
            else:
                _logger.error(_('There is nothing to reverse'))
                raise orm.except_orm(
                    _('Error'), _('There is nothing to reverse'))
        else:
            # check if the movement is link to an invoice
            if context['active_ids']:
                invoice_ids = inv_obj.search(
                    cr, uid,
                    [('accrual_move_id', 'in', context['active_ids'])])
        res = super(account_move_reversal, self).action_reverse(
            cr, uid, ids, context=context)
        if invoice_ids:
            inv_obj.write(
                cr, uid, invoice_ids, {'accrual_move_name': False,
                                       'accrual_move_id': False})
        return res
