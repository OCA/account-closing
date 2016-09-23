# -*- coding: utf-8 -*-
##############################################################################
#
#    Authors: Laetitia Gangloff
#    Copyright (c) 2014 Acsone SA/NV (http://www.acsone.eu)
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

from openerp.osv import orm, fields
from openerp.tools.translate import _

from openerp import tools

from datetime import date, timedelta


class account_move_accrual(orm.TransientModel):
    _name = "account.move.accrue"
    _description = "Create accrual of draft invoices"

    _columns = {
        'date': fields.date(
            'Accrual Date',
            required=True,
            help="Enter the date of the accrual account entries. "
                 "By default, Odoo proposes the last day of "
                 "the previous month."),
        'period_id': fields.many2one(
            'account.period',
            'Accrual Period',
            domain=[('special', '=', False),
                    ('state', '=', 'draft')],
            help="If empty, take the period of the date."),
        'account_id': fields.many2one(
            'account.account',
            'Accrual account',
            required=True,),
        'journal_id': fields.many2one(
            'account.journal',
            'Accrual Journal',
            help=''),
        'move_prefix': fields.char(
            'Entries Ref. Prefix',
            size=32,
            help="Prefix that will be added to the 'Ref' of the journal "
                 "entry to create the 'Ref' of the "
                 "accrual journal entry (no space added after the prefix)."),
        'move_line_prefix': fields.char(
            'Items Name Prefix',
            size=32,
            help="Prefix that will be added to the name of the journal "
                 "item to create the name of the accrual "
                 "journal item (a space is added after the prefix)."),
    }

    def _default_date(self, cr, uid, context=None):
        return (date(date.today().year, date.today().month, 1) -
                timedelta(days=1)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)

    def _default_journal(self, cr, uid, context=None):
        if context is None:
            context = {}
        journal_id = False
        if context.get('active_model') and context.get('active_ids') \
                and context['active_model'] == 'account.invoice':
            inv = self.pool.get('account.invoice').browse(
                cr, uid, context['active_ids'])[0]
            if inv.type in ('out_invoice', 'out_refund'):
                journal_id = \
                    inv.company_id.default_accrual_revenue_journal_id.id or\
                    inv.company_id.default_cutoff_journal_id.id
            else:
                journal_id =\
                    inv.company_id.default_accrual_expense_journal_id.id or\
                    inv.company_id.default_cutoff_journal_id.id
        return journal_id

    def _default_account(self, cr, uid, context=None):
        if context is None:
            context = {}
        acc_id = False
        if context.get('active_model') and context.get('active_ids') \
                and context['active_model'] == 'account.invoice':
            inv = self.pool.get('account.invoice').browse(
                cr, uid, context['active_ids'])[0]
            if inv.type in ('out_invoice', 'out_refund') \
                    and inv.company_id.default_accrued_revenue_account_id.id:
                acc_id = inv.company_id.default_accrued_revenue_account_id.id
            elif inv.company_id.default_accrued_expense_account_id.id:
                acc_id = inv.company_id.default_accrued_expense_account_id.id
        return acc_id

    _defaults = {
        'date': _default_date,
        'move_line_prefix': 'ACC -',
        'journal_id': _default_journal,
        'account_id': _default_account,
    }

    def action_accrue(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        assert 'active_ids' in context, "active_ids missing in context"

        form = self.read(cr, uid, ids, context=context)[0]

        inv_obj = self.pool.get('account.invoice')
        inv_ids = context['active_ids']

        period_id = form['period_id'][0] if form.get('period_id') else False
        journal_id = form['journal_id'][0] if form.get('journal_id') else False

        accrual_move_ids = inv_obj.create_accruals(
            cr, uid,
            inv_ids,
            form['date'],
            form['account_id'][0],
            accrual_period_id=period_id,
            accrual_journal_id=journal_id,
            move_prefix=form['move_prefix'],
            move_line_prefix=form['move_line_prefix'],
            context=context)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Accrual Entries'),
            'res_model': 'account.move',
            'domain': [('id', 'in', accrual_move_ids)],
            "views": [[False, "tree"], [False, "form"]],
        }
