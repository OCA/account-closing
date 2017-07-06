# -*- coding: utf-8 -*-
# Copyright 2012-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from openerp import models, api, fields


class UnrealizedCurrencyReportPrinter(models.TransientModel):
    _name = "unrealized.report.printer"

    account_ids = fields.Many2many(
        'account.account',
        string='Accounts (leave blank to select all)',
        domain="[('currency_revaluation', '=', True)]"
    )

    @api.multi
    def print_report(self, data):
        """
        Show the report
        """
        form = {}

        if not self.account_ids:
            form['account_ids'] = self.env['account.account'].search([
                ('currency_revaluation', '=', True)
            ]).ids
        else:
            form['account_ids'] = self.account_ids.ids

        data['form'] = form

        return {'type': 'ir.actions.report.xml',
                'report_name':
                    'account_multicurrency_revaluation_report.curr_unrealized',
                'datas': data}
