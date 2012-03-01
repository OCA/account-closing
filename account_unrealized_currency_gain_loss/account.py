# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Yannick Vaucher, Guewen Baconnier
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

from osv import osv, fields


class AccountAccount(osv.osv):
    _inherit='account.account'
    
    _columns = {'currency_revaluation': fields.boolean("Allow Currency revaluation")}

    _defaults = {'currency_revaluation': False}

    def _revaluation_query(self,
                           cr, uid,
                           ids,
                           revaluation_date,
                           context=None):
        mapping = {
            'balance': "COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance",
            'debit': "COALESCE(SUM(l.debit), 0) as debit",
            'credit': "COALESCE(SUM(l.credit), 0) as credit",
            'foreign_balance': "COALESCE(SUM(l.amount_currency), 0) as foreign_balance"
        }

        lines_where_clause = self.pool.get('account.move.line').\
            _query_get(cr, uid, context=context)

        query = ("SELECT l.account_id as id, l.partner_id, l.currency_id, " +
                   ', '.join(mapping.values()) +
                   " FROM account_move_line l "
                   " WHERE l.account_id IN %(account_ids)s AND "
                   " l.date <= %(revaluation_date)s AND "
                   " l.currency_id IS NOT NULL AND "
                        + lines_where_clause +
                   " GROUP BY l.account_id, l.currency_id, l.partner_id")
        params = {'revaluation_date': revaluation_date,
                  'account_ids': tuple(ids)}
        return query, params

    def compute_revaluations(
            self, cr, uid, ids, period_ids,
            revaluation_date, context=None):
        if context is None: context = {}
        accounts = {}

        #compute for each account the balance/debit/credit from the move lines
        ctx_query = context.copy()
        ctx_query['periods'] = period_ids
        query, params = self._revaluation_query(
            cr, uid, ids,
            revaluation_date,
            context=ctx_query)

        print cr.mogrify(query, params)
        cr.execute(query, params)

        lines = cr.dictfetchall()
        for line in lines:
            # generate a tree
            # - account_id
            # -- currency_id
            # --- partner_id
            # ----- balances
            account_id, currency_id, partner_id = \
                line['id'], line['currency_id'], line['partner_id']

            accounts.setdefault(account_id, {})
            accounts[account_id].setdefault(currency_id, {})
            accounts[account_id][currency_id].\
                setdefault(partner_id, {})
            accounts[account_id][currency_id][partner_id] = line

        return accounts

AccountAccount()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
