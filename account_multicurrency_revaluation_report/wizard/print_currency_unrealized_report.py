# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier, Yannick Vaucher
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
