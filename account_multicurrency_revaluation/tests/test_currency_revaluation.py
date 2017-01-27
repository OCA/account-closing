# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp.tests.common import TransactionCase


class TestCurrencyRevaluation(TransactionCase):

    def test_wizard(self):

        wizard = self.env['wizard.currency.revaluation']
        data = {
            'revaluation_date': '2017-03-15',
            'journal_id':
                self.env.ref('account_multicurrency_revaluation.'
                             'reval_journal').id,
            'label': '[%(account)s] wiz_test',
        }
        wiz = wizard.create(data)
        result = wiz.revaluate_currency()

        self.assertEquals(result.get('name'), "Created revaluation lines")

        # TODO asserts

    def setUp(self):
        super(TestCurrencyRevaluation, self).setUp()

        # Set accounts on company
        company = self.env['res.company'].search([])
        values = {
            'revaluation_loss_account_id':
                self.env.ref('account_multicurrency_revaluation.'
                             'acc_reval_loss').id,
            'revaluation_gain_account_id':
                self.env.ref('account_multicurrency_revaluation.'
                             'acc_reval_gain').id,
            'provision_bs_loss_account_id':
                self.env.ref('account_multicurrency_revaluation.'
                             'acc_prov_bs_loss').id,
            'provision_bs_gain_account_id':
                self.env.ref('account_multicurrency_revaluation.'
                             'acc_prov_bs_gain').id,
            'provision_pl_loss_account_id':
                self.env.ref('account_multicurrency_revaluation.'
                             'acc_prov_pl_loss').id,
            'provision_pl_gain_account_id':
                self.env.ref('account_multicurrency_revaluation.'
                             'acc_prov_pl_gain').id,
            'currency_id': self.env.ref('base.EUR').id
        }
        company.write(values)

        bank_journal = \
            self.env.ref('account_multicurrency_revaluation.bank_journal')
        sales_journal = \
            self.env.ref('account_multicurrency_revaluation.sales_journal')

        receivable_acc = \
            self.env.ref('account_multicurrency_revaluation.'
                         'wiz_test_acc_usd_receivable')
        revenue_acc = self.env.ref('account_multicurrency_revaluation.'
                                   'wiz_test_acc_usd_revenue')

        usd_currency = self.env.ref('base.USD')

        invoice_line_data = {
            'product_id': self.env.ref('product.product_product_5').id,
            'quantity': 1.0,
            'account_id': revenue_acc.id,
            'name': 'product test 5',
            'price_unit': 800.00,
        }

        invoice = self.env['account.invoice'].create({
            'name': "Customer Invoice",
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

        payment = self.env['account.payment'].create({
            'invoice_ids': [(4, invoice.id, 0)],
            'amount': 700,
            'currency_id': usd_currency.id,
            'payment_date': '2017-02-15',
            'communication': 'Invoice partial payment',
            'partner_id': invoice.partner_id.id,
            'partner_type': 'customer',
            'journal_id': bank_journal.id,
            'payment_type': 'inbound',
            'payment_method_id': payment_method.id,
            'payment_difference_handling': 'open',
            'writeoff_account_id': False,
        })
        payment.post()
