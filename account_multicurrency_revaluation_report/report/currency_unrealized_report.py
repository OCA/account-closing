# -*- coding: utf-8 -*-
# Copyright 2012-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp import pooler, models


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

    def get_lines(self):
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
                 ORDER BY res_partner.name,
                   account_move_line.gl_foreign_balance,
                   account_move_line.date"""
        self.cursor.execute(sql, [self.account_id])
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

    def __init__(self, cursor, uid, name, context):
        super(CurrencyUnrealizedReport, self).__init__(
            cursor, uid, name, context=context)

        self.pool = pooler.get_pool(self.cr.dbname)
        self.cursor = self.cr
        self.uid = uid
        self.company = self.pool.get('res.users').browse(
            self.cr, uid, uid, context=context).company_id
        self.localcontext.update({
            'report_name': _('Exchange Rate Gain and Loss Report'),
        })

    def set_context(self, objects, data, ids, report_type=None):
        """Populate a ledger_lines attribute on each browse record that will
        be used by mako template.
        """
        # we replace object
        objects = []

        # Redefine data['form'] so we can call report as HTML without
        # wizard on          https://root_server_address/report/html/
        # account_multicurrency_revaluation_report.curr_unrealized
        if not data.get('form'):
            data['form'] = {}
            data['form']['account_ids'] = self.pool('account.account').search(
                self.cr, self.uid, [('currency_revaluation', '=', True)])
            data['lang'] = 'en_US'
            data['uid'] = self.uid
            data['params'] = {}

        accounts = self.pool.get('account.account').browse(
            self.cr, self.uid, data['form'].get('account_ids')).sorted()

        for account in accounts:
            acc = ShellAccount(
                self.cursor, self.uid, self.pool, account.id,
                context=self.localcontext)
            if not acc.currency_revaluation:
                continue
            acc.get_lines()
            if acc.ordered_lines:
                objects.append(acc)
                acc.compute_totals()
        return super(CurrencyUnrealizedReport, self).set_context(
            objects, data, ids, report_type=None)


class ReportPrintCurrencyUnrealized(models.AbstractModel):
    _name = 'report.account_multicurrency_revaluation_report.curr_unrealized'
    _inherit = 'report.abstract_report'
    _template = 'account_multicurrency_revaluation_report.curr_unrealized'
    _wrapped_report_class = CurrencyUnrealizedReport
