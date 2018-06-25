# Copyright 2012-2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import SavepointCase
from odoo import fields
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT


class TestCurrencyRevaluation(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ref = cls.env.ref

        company = cls.env['res.company'].create({
            'name': 'new_company'
        })

        # Set currency EUR on company
        values = {
            'currency_id': ref('base.EUR').id,
        }
        company.write(values)

        cls.reval_journal = ref(
            'account_multicurrency_revaluation.reval_journal')

        sales_journal = ref('account_multicurrency_revaluation.sales_journal')

        receivable_acc = ref(
            'account_multicurrency_revaluation.demo_acc_receivable')
        receivable_acc.write({'reconcile': True})

        revenue_acc = ref('account_multicurrency_revaluation.'
                          'demo_acc_revenue')

        # create invoice in USD
        usd_currency = ref('base.USD')

        bank_journal_usd = ref(
            'account_multicurrency_revaluation.bank_journal_usd')
        bank_journal_usd.currency_id = usd_currency.id

        invoice_line_data = {
            'product_id': ref('product.product_product_5').id,
            'quantity': 1.0,
            'account_id': revenue_acc.id,
            'name': 'product test 5',
            'price_unit': 800.00,
            'currency_id': usd_currency.id
        }

        partner = ref('base.res_partner_3')

        year = fields.Date.from_string(fields.Date.today()).strftime('%Y')

        invoice = cls.env['account.invoice'].create({
            'name': "Customer Invoice",
            'date_invoice': '%s-01-16' % year,
            'currency_id': usd_currency.id,
            'journal_id': sales_journal.id,
            'partner_id': partner.id,
            'account_id': receivable_acc.id,
            'invoice_line_ids': [(0, 0, invoice_line_data)]
        })
        # Validate invoice
        invoice.action_invoice_open()

        payment_method = ref('account.account_payment_method_manual_in')

        # Register partial payment
        payment = cls.env['account.payment'].create({
            'invoice_ids': [(4, invoice.id, 0)],
            'amount': 700,
            'currency_id': usd_currency.id,
            'payment_date': '%s-02-15' % year,
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
        gbp_currency = ref('base.GBP')

        bank_journal_gbp = ref(
            'account_multicurrency_revaluation.bank_journal_gbp')

        bank_journal_gbp.currency_id = gbp_currency.id

        invoice_line_data = {
            'product_id': cls.env.ref('product.product_product_5').id,
            'quantity': 1.0,
            'account_id': revenue_acc.id,
            'name': 'product test 5',
            'price_unit': 800.00,
            'currency_id': gbp_currency.id
        }

        invoice = cls.env['account.invoice'].create({
            'name': "Customer Invoice",
            'date_invoice': '%s-01-16' % year,
            'currency_id': gbp_currency.id,
            'journal_id': sales_journal.id,
            'partner_id': ref('base.res_partner_3').id,
            'account_id': receivable_acc.id,
            'invoice_line_ids': [(0, 0, invoice_line_data)]
        })
        # Validate invoice
        invoice.action_invoice_open()

        payment_method = ref('account.account_payment_method_manual_in')

        # Register partial payment
        payment = cls.env['account.payment'].create({
            'invoice_ids': [(4, invoice.id, 0)],
            'amount': 700,
            'currency_id': gbp_currency.id,
            'payment_date': '%s-02-15' % year,
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

    def test_uk_revaluation(self):
        # Set accounts on company
        company = self.env['res.company'].search([])

        values = {
            'revaluation_loss_account_id':
                self.env.ref('account_multicurrency_revaluation.'
                             'acc_reval_loss').id,
            'revaluation_gain_account_id':
                self.env.ref('account_multicurrency_revaluation.'
                             'acc_reval_gain').id,
            'default_currency_reval_journal_id': self.reval_journal.id,
        }
        company.write(values)

        wizard = self.env['wizard.currency.revaluation']
        data = {
            'revaluation_date': '%s-03-15' % fields.Date.from_string(
                fields.Date.today()).strftime('%Y'),
            'journal_id': self.reval_journal.id,
            'label': '[%(account)s] wiz_test',
        }
        wiz = wizard.create(data)
        result = wiz.revaluate_currency()

        # Assert the wizard show the created revaluation lines
        self.assertEqual(result.get('name'), "Created revaluation lines")

        reval_move_lines = self.env['account.move.line'].search([
            ('name', 'like', 'wiz_test')])

        # Assert 8 account.move.line were generated
        self.assertEqual(len(reval_move_lines), 8)

        for reval_line in reval_move_lines:
            if reval_line.account_id.name == 'Account Liquidity USD':
                self.assertFalse(reval_line.partner_id)
                self.assertEqual(reval_line.credit, 0.0)
                self.assertEqual(reval_line.debit, 105.0)
            elif reval_line.account_id.name == 'Account Liquidity GBP':
                self.assertFalse(reval_line.partner_id)
                self.assertEqual(reval_line.credit, 0.0)
                self.assertEqual(reval_line.debit, 105.0)
            elif reval_line.account_id.name == 'Account Receivable':
                self.assertIsNotNone(reval_line.partner_id.id)
                self.assertEqual(reval_line.credit, 185.0)
                self.assertEqual(reval_line.debit, 0.0)
            elif reval_line.account_id.name == 'Reval Gain':
                self.assertEqual(reval_line.credit, 105.0)
                self.assertEqual(reval_line.debit, 0.0)
            elif reval_line.account_id.name == 'Reval Loss':
                self.assertEqual(reval_line.credit, 0.0)
                self.assertEqual(reval_line.debit, 185.0)

    def test_defaults(self):
        self.env['res.config.settings'].create({
            'default_currency_reval_journal_id': self.reval_journal.id,
            'revaluation_loss_account_id':
                self.env.ref('account_multicurrency_revaluation.'
                             'acc_reval_loss').id,
            'revaluation_gain_account_id':
                self.env.ref('account_multicurrency_revaluation.'
                             'acc_reval_gain').id
        }).execute()

        wizard = self.env['wizard.currency.revaluation'].create({})

        self.assertEqual(wizard.revaluation_date,
                         fields.date.today().strftime(DATE_FORMAT))
        self.assertEqual(wizard.journal_id, self.reval_journal)
