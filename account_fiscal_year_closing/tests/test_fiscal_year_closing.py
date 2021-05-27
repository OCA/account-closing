#  -*- coding: utf-8 -*-
#  Copyright 2021 Simone Rubino - Agile Business Group
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import datetime

from odoo.addons.account.tests.account_test_classes import AccountingTestCase


class TestFiscalYearClosing (AccountingTestCase):

    def setUp(self):
        super(TestFiscalYearClosing, self).setUp()
        account_model = self.env['account.account']
        self.invoice_model = self.env['account.invoice']
        partner_model = self.env['res.partner']

        self.receivable_account = account_model.create({
            'name': 'Test closing receivable account',
            'code': 'TCRECA',
            'reconcile': True,
            'user_type_id': self.ref('account.data_account_type_receivable'),
        })
        self.revenue_account = account_model.create({
            'name': 'Test closing revenue account',
            'code': 'TCREVA',
            'reconcile': True,
            'user_type_id': self.ref('account.data_account_type_revenue'),
        })
        self.dest_account = account_model.create({
            'name': 'Test destination account',
            'code': 'TDESTA',
            'reconcile': True,
            'user_type_id': self.ref('account.data_account_type_revenue'),
        })
        partner1_id = partner_model.name_create("Test partner 1")[0]
        self.partner1 = partner_model.browse(partner1_id)
        partner2_id = partner_model.name_create("Test partner 2")[0]
        self.partner2 = partner_model.browse(partner2_id)

    def _create_invoice(self, partner, today):
        invoice = self.invoice_model.create({
            'name': "Test invoice 1",
            'date': today,
            'partner_id': partner.id,
            'account_id': self.receivable_account.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.ref('product.product_product_5'),
                'quantity': 10.0,
                'account_id': self.revenue_account.id,
                'name': 'product test 5',
                'price_unit': 100.00,
            })]
        })
        invoice.action_invoice_open()
        return invoice

    def test_partner_unreconcile_balance(self):
        """
        Check that the balance of every involved partner
        is taken into account for destination move.
        """
        today = datetime.date(2021, 1, 1)
        self._create_invoice(self.partner1, today)
        self._create_invoice(self.partner2, today)
        chart_id = self.ref('l10n_generic_coa.configurable_chart_template')
        config = self.env['account.fiscalyear.closing.template'].create({
            'name': "Test fiscal year closing",
            'chart_template_ids': [(4, chart_id)],
            'check_draft_moves': False,
            'move_config_ids': [(0, 0, {
                'name': "Test move configuration 1",
                'code': 'TMC1',
                'mapping_ids': [(0, 0, {
                    'name': "All accounts to destination",
                    'src_accounts': '%',
                    'dest_account': self.dest_account.code,
                })],
                'closing_type_ids': [(0, 0, {
                    'account_type_id': self.receivable_account.user_type_id.id,
                    'closing_type': 'unreconciled',
                })]
            })],
        })
        closing_model = self.env['account.fiscalyear.closing']
        closing = closing_model.new({
            'year': today.year,
            'closing_template_id': config.id,
        })
        closing._onchange_year()
        closing_vals = closing._convert_to_write(closing._cache)
        closing = closing_model.create(closing_vals)
        closing.action_load_template()
        closing.button_calculate()

        self.assertEqual(closing.state, 'calculated')
