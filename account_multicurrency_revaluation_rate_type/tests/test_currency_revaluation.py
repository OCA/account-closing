# -*- coding: utf-8 -*-
# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import date
from odoo.tools.safe_eval import safe_eval
from odoo.tests.common import SavepointCase


class TestCurrencyRevaluationType(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestCurrencyRevaluationType, cls).setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        ref = cls.env.ref
        cls.company = ref(
            'account_multicurrency_revaluation.res_company_reval')

        cls.usd = ref('base.USD')
        cls.eur = ref('base.EUR')
        cls.year = str(date.today().year)

        monthly_rate = cls.env['res.currency.rate.monthly']
        monthly_rates_to_create = [
            {'month': '04', 'rate': 1.20},
            {'month': '12', 'rate': 5.40},
        ]
        for r in monthly_rates_to_create:
            r.update({
                'year': cls.year,
                'currency_id': cls.usd.id,
                'company_id': cls.company.id,
            })
            monthly_rate.create(r)

        cls.jan_31 = '%s-01-31' % cls.year
        cls.apr_05 = '%s-04-05' % cls.year
        cls.dec_31 = '%s-12-31' % cls.year

        cls.company.revaluation_loss_account_id = \
            ref('account_multicurrency_revaluation.acc_reval_loss').id
        cls.company.revaluation_gain_account_id = \
            ref('account_multicurrency_revaluation.acc_reval_gain').id

        cls.env.user.write({
            'company_ids': [(4, cls.company.id, False)]
        })
        cls.env.user.company_id = cls.company

        cls.reval_journal = ref(
            'account_multicurrency_revaluation.reval_journal')

        sales_journal = ref('account_multicurrency_revaluation.sales_journal')

        receivable_acc = ref(
            'account_multicurrency_revaluation.demo_acc_receivable')
        receivable_acc.write({'reconcile': True})
        payable_acc = ref(
            'account_multicurrency_revaluation.demo_acc_payable')
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
        partner.company_id = cls.company.id
        partner.property_account_payable_id = receivable_acc.id
        partner.property_account_receivable_id = payable_acc.id

        payment_term = ref('account.account_payment_term')

        invoice = cls.env['account.invoice'].create({
            'name': "Customer Invoice",
            'date_invoice': cls.jan_31,
            'currency_id': usd_currency.id,
            'company_id': cls.company.id,
            'journal_id': sales_journal.id,
            'partner_id': partner.id,
            'account_id': receivable_acc.id,
            'invoice_line_ids': [(0, 0, invoice_line_data)],
            'payment_term_id': payment_term.id,
        })
        # Validate invoice
        invoice.action_invoice_open()

        payment_method = ref('account_multicurrency_revaluation.'
                             'account_payment_method_manual_in')

        # Register partial payment
        payment = cls.env['account.payment'].create({
            'invoice_ids': [(4, invoice.id, 0)],
            'amount': 500,
            'currency_id': usd_currency.id,
            'company_id': cls.company.id,
            'payment_date': cls.jan_31,
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

    def test_revaluation_loss(self):
        # We test that wizard take right currency rate - month rate instead
        # of daily rate

        # re-estimate date 01-31 rate 5.40
        # lines selected for revaluation
        # amount_currency(USD)  balance(EUR)   account_id
        #    500                 200           Account Liquidity USD
        #    300                 120           Account Receivable
        #
        # lines estimated on rate 2.5 get from  currency_rate_usd_2017_03
        #
        # in result we get 2 evaluation lines
        # 300/5.4 = 55.56 - 120 = -64.44
        # 500/5.4 = 92.59 - 200 = -107.41

        result = self.wizard_execute(self.dec_31, 'average')
        move_ids = self._get_move_ids(result)
        debit = move_ids.filtered(lambda s: s.debit > 0)
        self.assertEqual(sum(debit.mapped('balance')), 171.85)

    def test_revaluation_gain(self):
        # date 04-05 rate 1.20
        # lines selected for revaluation same
        # in result we get 2 evaluation lines
        # 300/1.2 = 250 - 120 = 130
        # 500/1.2 = 416.67 - 200 = 216.67

        result = self.wizard_execute(self.apr_05, 'average')
        move_ids = self._get_move_ids(result)
        debit = move_ids.filtered(lambda s: s.credit > 0)
        self.assertEqual(sum(debit.mapped('balance')), -346.67)

    def _get_move_ids(self, result):
        return self.env['account.move.line'].\
            browse(safe_eval(result['domain'])[0][2])

    def wizard_execute(self, date, rate_type):

        data = {
            'revaluation_date': date,
            'journal_id': self.reval_journal.id,
            'label': '[%(account)s] [%(currency)s] wiz_test',
            'revaluation_rate_type': rate_type,
        }
        wiz = self.env['wizard.currency.revaluation'].create(data)
        return wiz.revaluate_currency()
