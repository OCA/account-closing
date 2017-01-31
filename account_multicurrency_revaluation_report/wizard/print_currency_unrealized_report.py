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

from openerp import models, api


class UnrealizedCurrencyReportPrinter(models.TransientModel):
    _name = "unrealized.report.printer"

    @api.multi
    def print_report(self, data):
        """
        Show the report
        """
        # context = self.env.context or {}
        # we update form with display account value
        # if isinstance(self, list):
        #     wid = wid[0]
        # current = self.browse(cursor, uid, wid, context=context)
        form = {}
        # form['period_id'] = current.period_id.id
        # form['period_name'] = current.period_id.name
        form['account_ids'] = [account.id for account in
                               self.env['account.account'].search([])]
        data['form'] = form

        return {'type': 'ir.actions.report.xml',
                'report_name':
                    'account_multicurrency_revaluation_report.curr_unrealized',
                'datas': data}
