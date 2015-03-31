# -*- coding: utf-8 -*-
##############################################################################
#
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

from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp import pooler


class ShellAccount(object):
    # Small class that avoid to override account account object
    # only for pure perfomance reason.
    # Browsing an account account object is not efficient
    # beacause of function fields
    # This object aim to be easly transpose to account account if needed
    def exists(self):
        return True

    def __init__(self, cr, uid, pool, acc_id, context=None):
        self._context = context or {}
        self.cursor = cr
        self.uid = uid
        self.acc_id = acc_id
        self.pool = pool
        tmp = self.pool['account.account'].read(
            cr, uid, [acc_id], ['id', 'name', 'code', 'currency_revaluation'],
            self._context)
        self.name = tmp[0].get('name')
        self.code = tmp[0].get('code')
        self.account_id = tmp[0]['id']
        self.ordered_lines = []
        self.company_id = self.pool['res.users'].browse(
            cr, uid, uid, context=context).company_id
        self.currency_revaluation = tmp[0].get('currency_revaluation', False)
        self.keys_to_sum = ['gl_foreign_balance', 'gl_currency_rate',
                            'gl_revaluated_balance', 'gl_balance',
                            'gl_ytd_balance']

    def __contains__(self, key):
        return hasattr(self, key)

    def get_lines(self, period_id):
        """Get all line account move line that are need on report for current
        account.
        """
        sql = """Select res_partner.name,
                   account_move_line.date,
                   account_move_line.gl_foreign_balance,
                   account_move_line.gl_currency_rate,
                   account_move_line.gl_revaluated_balance,
                   account_move_line.gl_balance,
                   account_move_line.gl_revaluated_balance -
                   account_move_line.gl_balance as gl_ytd_balance,
                   res_currency.name as curr_name
                 FROM account_move_line
                   LEFT join res_partner on
                     (account_move_line.partner_id = res_partner.id)
                   LEFT join account_move on
                     (account_move_line.move_id = account_move.id)
                   LEFT join res_currency on
                     (account_move_line.currency_id = res_currency.id)
                 WHERE account_move_line.account_id = %s
                   AND account_move.to_be_reversed = true
                   AND account_move_line.gl_balance is not null
                   AND account_move_line.period_id = %s
                 ORDER BY res_partner.name,
                   account_move_line.gl_foreign_balance,
                   account_move_line.date"""
        self.cursor.execute(sql, (self.account_id, period_id))
        self.ordered_lines = self.cursor.dictfetchall()
        return self.ordered_lines

    def compute_totals(self):
        """Compute the sum of values in self.ordered_lines"""
        totals = dict.fromkeys(self.keys_to_sum, 0.0)
        for line in self.ordered_lines:
            for tot in self.keys_to_sum:
                totals[tot] += line.get(tot, 0.0)
        for key, val in totals.iteritems():
            setattr(self, key + '_total', val)


class CurrencyUnrealizedReport(report_sxw.rml_parse):

    def _get_period_name(self, data):
        return data.get('form', {}).get('period_name', '')

    def __init__(self, cursor, uid, name, context):
        super(CurrencyUnrealizedReport, self).__init__(
            cursor, uid, name, context=context)
        self.pool = pooler.get_pool(self.cr.dbname)
        self.cursor = self.cr
        self.company = self.pool.get('res.users').browse(
            self.cr, uid, uid, context=context).company_id
        self.localcontext.update({
            'cr': cursor,
            'uid': uid,
            'period_name': self._get_period_name,
            'report_name': _('Exchange Rate Gain and Loss Report')}
        )

    def sort_accounts_with_structure(self, root_account_ids, account_ids,
                                     context=None):
        """Sort accounts by code respecting their structure. code Take from
        financial webkit report in order not to depends from it"""

        def recursive_sort_by_code(accounts, parent):
            sorted_accounts = []
            # add all accounts with same parent
            level_accounts = [account for account in accounts
                              if account['parent_id'] and
                              account['parent_id'][0] == parent['id']]
            # add consolidation children of parent, as they are logically on
            # the same level
            if parent.get('child_consol_ids'):
                level_accounts.extend([account for account in accounts
                                       if account['id'] in
                                       parent['child_consol_ids']])
            # stop recursion if no children found
            if not level_accounts:
                return []
            level_accounts = sorted(level_accounts, key=lambda a: a['code'])
            for level_account in level_accounts:
                sorted_accounts.append(level_account['id'])
                sorted_accounts.extend(
                    recursive_sort_by_code(accounts, parent=level_account))
            return sorted_accounts
        if not account_ids:
            return []
        accounts_data = self.pool['account.account'].read(
            self.cr, self.uid, account_ids,
            ['id', 'parent_id', 'level', 'code', 'child_consol_ids'],
            context=context)
        sorted_accounts = []
        root_accounts_data = [account_data for account_data in accounts_data
                              if account_data['id'] in root_account_ids]
        for root_account_data in root_accounts_data:
            sorted_accounts.append(root_account_data['id'])
            sorted_accounts.extend(
                recursive_sort_by_code(accounts_data, root_account_data))
        # fallback to unsorted accounts when sort failed
        # sort fails when the levels are miscalculated by account.account
        # check lp:783670
        if len(sorted_accounts) != len(account_ids):
            sorted_accounts = account_ids

        return sorted_accounts

    def get_all_accounts(self, account_ids, exclude_type=None, only_type=None,
                         filter_report_type=None, context=None):
        """Get all account passed in params with their childrens.
        TAKEN FROM webkit general ledger

        @param exclude_type: list of types to exclude (view, receivable,
          payable, consolidation, other)
        @param only_type: list of types to filter on (view, receivable,
          payable, consolidation, other)
        @param filter_report_type: list of report type to filter on
        """
        context = context or {}
        accounts = []
        if not isinstance(account_ids, list):
            account_ids = [account_ids]
        acc_obj = self.pool.get('account.account')
        for account_id in account_ids:
            accounts.append(account_id)
            accounts += acc_obj._get_children_and_consol(
                self.cursor, self.uid, account_id, context=context)
        res_ids = list(set(accounts))
        res_ids = self.sort_accounts_with_structure(
            account_ids, res_ids, context=context)

        if exclude_type or only_type or filter_report_type:
            sql_filters = {'ids': tuple(res_ids)}
            sql_select = "SELECT a.id FROM account_account a"
            sql_join = ""
            sql_where = "WHERE a.id IN %(ids)s"
            if exclude_type:
                sql_where += " AND a.type not in %(exclude_type)s"
                sql_filters.update({'exclude_type': tuple(exclude_type)})
            if only_type:
                sql_where += " AND a.type IN %(only_type)s"
                sql_filters.update({'only_type': tuple(only_type)})
            if filter_report_type:
                sql_join += "INNER JOIN account_account_type t" \
                            " ON t.id = a.user_type"
                sql_join += " AND t.report_type IN %(report_type)s"
                sql_filters.update({'report_type': tuple(filter_report_type)})

            sql_join += " order by account_account.code"

            sql = ' '.join((sql_select, sql_join, sql_where))
            self.cursor.execute(sql, sql_filters)
            fetch_only_ids = self.cursor.fetchall()
            if not fetch_only_ids:
                return []
            only_ids = [only_id[0] for only_id in fetch_only_ids]
            # keep sorting but filter ids
            res_ids = [res_id for res_id in res_ids if res_id in only_ids]
        return res_ids

    def set_context(self, objects, data, ids, report_type=None):
        """Populate a ledger_lines attribute on each browse record that will
        be used by mako template.
        """
        for mand in ['account_ids', 'period_id']:
            if not data['form'][mand]:
                raise Exception(
                    _('%s argument is not set in wizard') % (mand,))
        # we replace object
        objects = []
        new_ids = data['form']['account_ids']
        period_id = data['form']['period_id']
        # get_all_account is in charge of ordering the accounts
        for acc_id in self.get_all_accounts(new_ids):
            acc = ShellAccount(
                self.cursor, self.uid, self.pool, acc_id,
                context=self.localcontext)
            if not acc.currency_revaluation:
                continue
            acc.get_lines(period_id)
            if acc.ordered_lines:
                objects.append(acc)
                acc.compute_totals()
        return super(CurrencyUnrealizedReport, self).set_context(
            objects, data, ids, report_type=None)

report_sxw.report_sxw(
    'report.currency_unrealized', 'account.account',
    'addons/account_multicurrency_revaluation/report/templates/'
    'unrealized_currency_gain_loss.mako', parser=CurrencyUnrealizedReport)
