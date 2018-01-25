# Copyright 2014 ACSONE SA/NV (http://acsone.eu)
# @author Stéphane Bidoul <stephane.bidoul@acsone.eu>
# Copyright 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import time
from odoo import fields
from odoo.tests.common import SavepointCase


class TestCutoffPrepaid(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.inv_model = cls.env['account.invoice']
        cls.cutoff_model = cls.env['account.cutoff']
        cls.account_model = cls.env['account.account']
        cls.journal_model = cls.env['account.journal']
        cls.account_expense = cls.account_model.search([(
            'user_type_id',
            '=',
            cls.env.ref('account.data_account_type_expenses').id)], limit=1)
        cls.account_payable = cls.account_model.search([(
            'user_type_id',
            '=',
            cls.env.ref('account.data_account_type_payable').id)], limit=1)
        cls.account_cutoff = cls.account_model.search([(
            'user_type_id',
            '=',
            cls.env.ref('account.data_account_type_current_liabilities').id)],
            limit=1)
        cls.cutoff_journal = cls.journal_model.search([], limit=1)
        cls.purchase_journal = cls.journal_model.search([(
            'type', '=', 'purchase')], limit=1)

    def _date(self, date):
        """ convert MM-DD to current year date YYYY-MM-DD """
        return time.strftime('%Y-' + date)

    def _days(self, start_date, end_date):
        start_date = fields.Date.from_string(self._date(start_date))
        end_date = fields.Date.from_string(self._date(end_date))
        return (end_date - start_date).days + 1

    def _create_invoice(self, date, amount, start_date, end_date):
        invoice = self.inv_model.create({
            'date_invoice': self._date(date),
            'account_id': self.account_payable.id,
            'partner_id': self.env.ref('base.res_partner_2').id,
            'journal_id': self.purchase_journal.id,
            'type': 'in_invoice',
            'invoice_line_ids': [(0, 0, {
                'name': 'expense',
                'price_unit': amount,
                'quantity': 1,
                'account_id': self.account_expense.id,
                'start_date': self._date(start_date),
                'end_date': self._date(end_date),
            })],
        })
        invoice.action_invoice_open()
        self.assertEqual(amount, invoice.amount_untaxed)
        return invoice

    def _create_cutoff(self, date):
        cutoff = self.cutoff_model.create({
            'cutoff_date': self._date(date),
            'cutoff_type': 'prepaid_revenue',
            'cutoff_journal_id': self.cutoff_journal.id,
            'cutoff_account_id': self.account_cutoff.id,
            'source_journal_ids': [(6, 0, [self.purchase_journal.id])],
        })
        return cutoff

    def test_with_cutoff_before_after_and_in_the_middle(self):
        """ basic test with cutoff before, after and in the middle """
        amount = self._days('04-01', '06-30')
        amount_2months = self._days('05-01', '06-30')
        # invoice to be spread of 3 months
        self._create_invoice('01-15', amount,
                             start_date='04-01', end_date='06-30')
        # cutoff after one month of invoice period -> 2 months cutoff
        cutoff = self._create_cutoff('04-30')
        cutoff.get_prepaid_lines()
        self.assertEqual(amount_2months, cutoff.total_cutoff_amount)
        # cutoff at end of invoice period -> no cutoff
        cutoff = self._create_cutoff('06-30')
        cutoff.get_prepaid_lines()
        self.assertEqual(0, cutoff.total_cutoff_amount)
        # cutoff before invoice period -> full value cutoff
        cutoff = self._create_cutoff('01-31')
        cutoff.get_prepaid_lines()
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
        cutoff = self._create_cutoff('01-31')
        cutoff.get_prepaid_lines()
        cutoff.create_move()
        self.assertEqual(amount * 2, cutoff.total_cutoff_amount)
        self.assertTrue(cutoff.move_id, "move not generated")
        # two invoices, but two lines (because the two cutoff lines
        # have been grouped into one line plus one counterpart)
        self.assertEqual(len(cutoff.move_id.line_ids), 2)
