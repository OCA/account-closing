# -*- coding: utf-8 -*-
# Copyright 2012-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.tests.common import TransactionCase


class TestCurrencyRevaluationReport(TransactionCase):

    def test_wizard_empty_accounts(self):
        wizard = self.env['unrealized.report.printer']
        wiz = wizard.create({})
        data = {'lang': 'en_US',
                'params': {'action': 254},
                'tz': 'Europe/Brussels',
                'uid': 1}
        result = wiz.print_report(data)

        self.assertEquals(result.get('type'), "ir.actions.report.xml")
        self.assertEquals(
            result.get('report_name'),
            "account_multicurrency_revaluation_report.curr_unrealized")
