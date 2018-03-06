# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tests.common import TransactionCase


class TestAccountCutoffAccrualReturn(TransactionCase):

    def setUp(self):
        super(TestAccountCutoffAccrualReturn, self).setUp()
        self.company = self.env.ref('base.main_company')
        self.accrual_journal = self.env['account.journal'].create({
            'code': 'cop0',
            'company_id': self.company.id,
            'name': 'Accrual Journal Return',
            'type': 'general'})
        user_type_lia = self.env.ref(
            'account.data_account_type_current_liabilities')
        self.accrual_account = self.env['account.account'].create({
            'name': 'Accrual account',
            'code': 'ACC480000',
            'company_id': self.company.id,
            'user_type_id': user_type_lia.id
        })
        self.company.write({
            'default_accrued_revenue_account_id': self.accrual_account.id,
            'default_accrued_expense_account_id': self.accrual_account.id,
            'default_cutoff_journal_id': self.accrual_journal.id
        })
        self.product_1 = self.env.ref('product.product_delivery_01')

    def test_accrued_revenue_return(self):
        location = self.env['stock.location'].create({
            'name': 'Return Customer Accrual',
            'accrued_customer_return': 1,
            })

        # Prepare cutoff
        type = 'accrued_revenue_return'
        cutoff = self.env['account.cutoff'].with_context(default_type=type)\
            .create({
                'type': type,
                'company_id': 1,
                'cutoff_date': datetime.today() + relativedelta(days=+15),
            })
        cutoff.get_lines()
        self.assertTrue(
            len(cutoff.line_ids) == 0, 'There should be no line to process')

        # Put product in return location
        inventory = self.env['stock.inventory'].create({
            'name': 'Starting for product_1',
            'filter': 'product',
            'location_id': location.id,
            'product_id': self.product_1.id,
        })
        inventory.prepare_inventory()
        inventory.line_ids.unlink()
        inventory.line_ids.create({
            'product_id': self.product_1.id,
            'product_qty': 35.0,
            'inventory_id': inventory.id,
            'location_id': location.id,
            })
        inventory.action_done()

        # Check cutoff
        cutoff.get_lines()
        self.assertTrue(len(cutoff.line_ids) == 1,
                        '1 cutoff line should be found')
        for line in cutoff.line_ids:
            price = self.product_1.standard_price
            self.assertTrue(line.cutoff_amount == 35*price,
                            'Return line cutoff amount incorrect')

    def test_accrued_expense_return(self):
        location = self.env['stock.location'].create({
            'name': 'Return Supplier Accrual',
            'accrued_supplier_return': 1,
            })

        # Prepare cutoff
        type = 'accrued_expense_return'
        cutoff = self.env['account.cutoff'].with_context(default_type=type)\
            .create({
                'type': type,
                'company_id': 1,
                'cutoff_date': datetime.today() + relativedelta(days=+15),
            })
        cutoff.get_lines()
        self.assertTrue(
            len(cutoff.line_ids) == 0, 'There should be no line to process')

        # Put product in return location
        inventory = self.env['stock.inventory'].create({
            'name': 'Starting for product_1',
            'filter': 'product',
            'location_id': location.id,
            'product_id': self.product_1.id,
        })
        inventory.prepare_inventory()
        inventory.line_ids.unlink()
        inventory.line_ids.create({
            'product_id': self.product_1.id,
            'product_qty': 35.0,
            'inventory_id': inventory.id,
            'location_id': location.id,
            })
        inventory.action_done()

        # Check cutoff
        cutoff.get_lines()
        self.assertTrue(len(cutoff.line_ids) == 1,
                        '1 cutoff line should be found')
        for line in cutoff.line_ids:
            price = self.product_1.standard_price
            self.assertTrue(line.cutoff_amount == 35*price,
                            'Return line cutoff amount incorrect')
