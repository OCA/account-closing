# -*- encoding: utf-8 -*-
##############################################################################
#
#    Account Cut-off Prepaid test module for OpenERP
#    Copyright (C) 2014 ACSONE SA/NV (http://acsone.eu)
#    @author Stéphane Bidoul <stephane.bidoul@acsone.eu>
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

import time

from dateutil.parser import parse as parse_date

import openerp.tests.common as common
from openerp import workflow


class TestCutoffPrepaid(common.TransactionCase):

    def setUp(self):
        super(TestCutoffPrepaid, self).setUp()
        self.inv_model = self.registry('account.invoice')
        self.cutoff_model = self.registry('account.cutoff')

    def _date(self, date):
        """ convert MM-DD to current year date YYYY-MM-DD """
        return time.strftime('%Y-' + date)

    def _days(self, start_date, end_date):
        start_date = parse_date(self._date(start_date))
        end_date = parse_date(self._date(end_date))
        return (end_date - start_date).days + 1

    def _create_invoice(self, date, amount, start_date, end_date):
        inv_id = self.inv_model.create(self.cr, self.uid, {
            'journal_id': self.ref('account.expenses_journal'),
            'date_invoice': self._date(date),
            'account_id': self.ref('account.a_recv'),
            'partner_id': self.ref('base.res_partner_17'),
            'type': 'in_invoice',
            'invoice_line': [(0, 0, {
                'name': 'expense',
                'price_unit': amount,
                'quantity': 1,
                'account_id': self.ref('account.a_expense'),
                'start_date': self._date(start_date),
                'end_date': self._date(end_date),
            })],
        })
        workflow.trg_validate(self.uid, 'account.invoice', inv_id,
                              'invoice_open', self.cr)
        inv = self.inv_model.browse(self.cr, self.uid, inv_id)
        self.assertEqual(amount, inv.amount_untaxed)
        return inv_id

    def _create_cutoff(self, date):
        cutoff_id = self.cutoff_model.create(self.cr, self.uid, {
            'cutoff_date': self._date(date),
            'type': 'prepaid_revenue',
            'cutoff_journal_id': self.ref('account.miscellaneous_journal'),
            'cutoff_account_id': self.ref('account.o_expense'),
            'source_journal_ids': [
                (6, 0, [self.ref('account.expenses_journal')]),
            ],
        })
        return cutoff_id

    def test_0(self):
        """ basic test with cutoff before, after and in the middle """
        amount = self._days('04-01', '06-30')
        amount_2months = self._days('05-01', '06-30')
        # invoice to be spread of 3 months
        self._create_invoice('01-15', amount,
                             start_date='04-01', end_date='06-30')
        # cutoff after one month of invoice period -> 2 months cutoff
        cutoff_id = self._create_cutoff('04-30')
        self.cutoff_model.get_prepaid_lines(self.cr, self.uid, [cutoff_id])
        cutoff = self.cutoff_model.browse(self.cr, self.uid, cutoff_id)
        self.assertEqual(amount_2months, cutoff.total_cutoff_amount)
        # cutoff at end of invoice period -> no cutoff
        cutoff_id = self._create_cutoff('06-30')
        self.cutoff_model.get_prepaid_lines(self.cr, self.uid, [cutoff_id])
        cutoff = self.cutoff_model.browse(self.cr, self.uid, cutoff_id)
        self.assertEqual(0, cutoff.total_cutoff_amount)
        # cutoff before invoice period -> full value cutoff
        cutoff_id = self._create_cutoff('01-31')
        self.cutoff_model.get_prepaid_lines(self.cr, self.uid, [cutoff_id])
        cutoff = self.cutoff_model.browse(self.cr, self.uid, cutoff_id)
        self.assertEqual(amount, cutoff.total_cutoff_amount)

    def tests_1(self):
        """ generate move, and test move lines grouping """
        # two invoices
        amount = self._days('04-01', '06-30')
        self._create_invoice('01-15', amount,
                             start_date='04-01', end_date='06-30')
        self._create_invoice('01-16', amount,
                             start_date='04-01', end_date='06-30')
        # cutoff before invoice period -> full value cutoff
        cutoff_id = self._create_cutoff('01-31')
        self.cutoff_model.get_prepaid_lines(self.cr, self.uid, [cutoff_id])
        self.cutoff_model.create_move(self.cr, self.uid, [cutoff_id])
        cutoff = self.cutoff_model.browse(self.cr, self.uid, cutoff_id)
        self.assertEqual(amount * 2, cutoff.total_cutoff_amount)
        self.assert_(cutoff.move_id, "move not generated")
        # two invoices, but two lines (because the two cutoff lines
        # have been grouped into one line plus one counterpart)
        self.assertEqual(len(cutoff.move_id.line_id), 2)
