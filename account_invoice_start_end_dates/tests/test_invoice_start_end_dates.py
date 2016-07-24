# -*- coding: utf-8 -*-
# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import time
from openerp.tools import float_compare
from openerp.tests.common import TransactionCase


class TestInvoiceStartEndDates(TransactionCase):

    def setUp(self):
        super(TestInvoiceStartEndDates, self).setUp()
        self.inv_model = self.env['account.invoice']
        self.account_model = self.env['account.account']
        self.journal_model = self.env['account.journal']
        self.account_revenue = self.account_model.search([(
            'user_type_id',
            '=',
            self.env.ref('account.data_account_type_revenue').id)], limit=1)
        self.account_receivable = self.account_model.search([(
            'user_type_id',
            '=',
            self.env.ref('account.data_account_type_receivable').id)], limit=1)
        self.cutoff_journal = self.journal_model.search([], limit=1)
        self.sale_journal = self.journal_model.search([(
            'type', '=', 'sale')], limit=1)
        # enable grouping on sale journal
        self.sale_journal.group_invoice_lines = True
        self.maint_product = self.env.ref(
            'account_invoice_start_end_dates.product_maintenance_contrat')

    def _date(self, date):
        """ convert MM-DD to current year date YYYY-MM-DD """
        return time.strftime('%Y-' + date)

    def test_invoice_with_grouping(self):
        invoice = self.inv_model.create({
            'date_invoice': self._date('01-01'),
            'account_id': self.account_receivable.id,
            'partner_id': self.env.ref('base.res_partner_2').id,
            'journal_id': self.sale_journal.id,
            'type': 'out_invoice',
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': self.maint_product.id,
                    'name': 'Maintenance IPBX 12 mois',
                    'price_unit': 2400,
                    'quantity': 1,
                    'account_id': self.account_revenue.id,
                    'start_date': self._date('01-01'),
                    'end_date': self._date('12-31'),
                    }),
                (0, 0, {
                    'product_id': self.maint_product.id,
                    'name': 'Maintenance téléphones 12 mois',
                    'price_unit': 12,
                    'quantity': 10,
                    'account_id': self.account_revenue.id,
                    'start_date': self._date('01-01'),
                    'end_date': self._date('12-31'),
                    }),
                (0, 0, {
                    'product_id': self.maint_product.id,
                    'name': 'Maintenance Fax 6 mois',
                    'price_unit': 120.75,
                    'quantity': 1,
                    'account_id': self.account_revenue.id,
                    'start_date': self._date('01-01'),
                    'end_date': self._date('06-30'),
                    }),
                (0, 0, {
                    'product_id':
                    self.env.ref('product.product_product_17').id,
                    'name': 'HD IPBX',
                    'price_unit': 215.5,
                    'quantity': 1,
                    'account_id': self.account_revenue.id,
                    }),
                ],
        })
        invoice.signal_workflow('invoice_open')
        self.assertTrue(invoice.move_id)
        iline_res = {
            (self._date('01-01'), self._date('12-31')): 2520,
            (self._date('01-01'), self._date('06-30')): 120.75,
            (False, False): 215.5,
            }
        precision = self.env['decimal.precision'].precision_get('Account')
        for mline in invoice.move_id.line_ids:
            if mline.account_id == self.account_revenue:
                amount = iline_res.pop((mline.start_date, mline.end_date))
                self.assertEquals(float_compare(
                    amount, mline.credit, precision_digits=precision), 0)
