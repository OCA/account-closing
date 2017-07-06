# -*- coding: utf-8 -*-
# Copyright 2012-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.tests.common import TransactionCase


class TestCurrencyRevaluation(TransactionCase):

    def test_uk_revaluation(self):
        # Set accounts on company
        company = self.env['res.company'].search([])

        reval_journal = self.env.ref(
            'account_multicurrency_revaluation.reval_journal')
        values = {
            'revaluation_loss_account_id':
                self.env.ref('account_multicurrency_revaluation.'
                             'acc_reval_loss').id,
            'revaluation_gain_account_id':
                self.env.ref('account_multicurrency_revaluation.'
                             'acc_reval_gain').id,
            'default_currency_reval_journal_id': reval_journal.id,
        }
        company.write(values)

        wizard = self.env['wizard.currency.revaluation']
        data = {
            'revaluation_date': '2017-03-15',
            'journal_id': reval_journal.id,
            'label': '[%(account)s] wiz_test',
        }
        wiz = wizard.create(data)
        result = wiz.revaluate_currency()

        # Assert the wizard show the created revaluation lines
        self.assertEquals(result.get('name'), "Created revaluation lines")

        reval_move_lines = self.env['account.move.line'].search([
            ('name', 'like', 'wiz_test')])

        # Assert 8 account.move.line were generated
        self.assertEquals(len(reval_move_lines), 8)

        for reval_line in reval_move_lines:
            if reval_line.account_id.name == 'Account Liquidity USD':
                self.assertFalse(reval_line.partner_id)
                self.assertEquals(reval_line.credit, 0.0)
                self.assertEquals(reval_line.debit, 105.0)
            elif reval_line.account_id.name == 'Account Liquidity GBP':
                self.assertFalse(reval_line.partner_id)
                self.assertEquals(reval_line.credit, 0.0)
                self.assertEquals(reval_line.debit, 105.0)
            elif reval_line.account_id.name == 'Account Receivable':
                self.assertIsNotNone(reval_line.partner_id.id)
                self.assertEquals(reval_line.credit, 185.0)
                self.assertEquals(reval_line.debit, 0.0)
            elif reval_line.account_id.name == 'Reval Gain':
                self.assertEquals(reval_line.credit, 105.0)
                self.assertEquals(reval_line.debit, 0.0)
            elif reval_line.account_id.name == 'Reval Loss':
                self.assertEquals(reval_line.credit, 0.0)
                self.assertEquals(reval_line.debit, 185.0)

    def setUp(self):
        super(TestCurrencyRevaluation, self).setUp()

        # Set currency EUR on company
        company = self.env['res.company'].search([])
        values = {
            'currency_id': self.env.ref('base.EUR').id
        }
        company.write(values)

        sales_journal = \
            self.env.ref('account_multicurrency_revaluation.sales_journal')

        receivable_acc = \
            self.env.ref('account_multicurrency_revaluation.'
                         'demo_acc_receivable')
        receivable_acc.write({'reconcile': True})

        revenue_acc = self.env.ref('account_multicurrency_revaluation.'
                                   'demo_acc_revenue')

        # create invoice in USD
        usd_currency = self.env.ref('base.USD')

        bank_journal_usd = \
            self.env.ref('account_multicurrency_revaluation.bank_journal_usd')

        invoice_line_data = {
            'product_id': self.env.ref('product.product_product_5').id,
            'quantity': 1.0,
            'account_id': revenue_acc.id,
            'name': 'product test 5',
            'price_unit': 800.00,
            'currency_id': usd_currency.id
        }

        invoice = self.env['account.invoice'].create({
            'name': "Customer Invoice",
            'date_invoice': '2017-01-16',
            'currency_id': usd_currency.id,
            'journal_id': sales_journal.id,
            'partner_id': self.env.ref('base.res_partner_3').id,
            'account_id': receivable_acc.id,
            'invoice_line_ids': [(0, 0, invoice_line_data)]
        })
        # Validate invoice
        invoice.signal_workflow('invoice_open')

        payment_method = \
            self.env.ref('account.account_payment_method_manual_in')

        # Register partial payment
        payment = self.env['account.payment'].create({
            'invoice_ids': [(4, invoice.id, 0)],
            'amount': 700,
            'currency_id': usd_currency.id,
            'payment_date': '2017-02-15',
            'communication': 'Invoice partial payment',
            'partner_id': invoice.partner_id.id,
            'partner_type': 'customer',
            'journal_id': bank_journal_usd.id,
            'payment_type': 'inbound',
            'payment_method_id': payment_method.id,
            'payment_difference_handling': 'open',
            'writeoff_account_id': False,
        })
        payment.post()

        # create invoice in GBP
        gbp_currency = self.env.ref('base.GBP')

        bank_journal_gbp = \
            self.env.ref('account_multicurrency_revaluation.bank_journal_gbp')

        invoice_line_data = {
            'product_id': self.env.ref('product.product_product_5').id,
            'quantity': 1.0,
            'account_id': revenue_acc.id,
            'name': 'product test 5',
            'price_unit': 800.00,
            'currency_id': gbp_currency.id
        }

        invoice = self.env['account.invoice'].create({
            'name': "Customer Invoice",
            'date_invoice': '2017-01-16',
            'currency_id': gbp_currency.id,
            'journal_id': sales_journal.id,
            'partner_id': self.env.ref('base.res_partner_3').id,
            'account_id': receivable_acc.id,
            'invoice_line_ids': [(0, 0, invoice_line_data)]
        })
        # Validate invoice
        invoice.signal_workflow('invoice_open')

        payment_method = \
            self.env.ref('account.account_payment_method_manual_in')

        # Register partial payment
        payment = self.env['account.payment'].create({
            'invoice_ids': [(4, invoice.id, 0)],
            'amount': 700,
            'currency_id': gbp_currency.id,
            'payment_date': '2017-02-15',
            'communication': 'Invoice partial payment',
            'partner_id': invoice.partner_id.id,
            'partner_type': 'customer',
            'journal_id': bank_journal_gbp.id,
            'payment_type': 'inbound',
            'payment_method_id': payment_method.id,
            'payment_difference_handling': 'open',
            'writeoff_account_id': False,
        })
        payment.post()
