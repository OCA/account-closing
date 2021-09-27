# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tests.common import TransactionCase


class TestAccountCutoffAccrualPicking(TransactionCase):

    def setUp(self):
        super(TestAccountCutoffAccrualPicking, self).setUp()
        self.company = self.env.ref('base.main_company')
        self.accrual_journal = self.env['account.journal'].create({
            'code': 'cop0',
            'company_id': self.company.id,
            'name': 'Accrual Journal Picking',
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

        self.partner = self.env.ref('base.res_partner_1')

    def test_accrued_revenue(self):
        """ Test complete so to process"""
        # Removing all existing SO
        self.env.cr.execute('DELETE FROM sale_order;')
        # Create SO
        self.products = [
            self.env.ref('product.product_delivery_01'),
            self.env.ref('product.product_delivery_02'),
        ]
        self.so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {
                'name': p.name,
                'product_id': p.id,
                'product_uom_qty': 2,
                'product_uom': p.uom_id.id,
                'price_unit': 100})
                for p in self.products],
            'pricelist_id': self.env.ref('product.list0').id,
        })

        type_cutoff = 'accrued_revenue'
        cutoff = self.env['account.cutoff']\
            .with_context(default_type=type_cutoff)\
            .create({
                'type': type_cutoff,
                'company_id': 1,
                'cutoff_date': datetime.today() + relativedelta(days=+15),
            })
        cutoff.get_lines()
        self.assertTrue(
            len(cutoff.line_ids) == 0, 'There should be no so line to process')

        self.so.action_confirm()
        self.assertEqual(
            self.so.invoice_status, 'no',
            'SO invoice_status should be "nothing to invoice" after invoicing')
        pick = self.so.picking_ids
        pick.force_assign()
        pick.pack_operation_product_ids.write({'qty_done': 1})
        wiz_act = pick.do_new_transfer()
        wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
        wiz.process()
        self.assertEqual(
            self.so.invoice_status, 'to invoice',
            'SO invoice_status should be "to invoice" after partial delivery')
        qties = [sol.qty_delivered for sol in self.so.order_line]
        self.assertEqual(
            qties, [1 for p in self.products],
            'Delivered quantities are wrong after partial delivery')

        cutoff.get_lines()
        self.assertTrue(len(cutoff.line_ids) == 2,
                        '2 cutoff lines should be found')
        for line in cutoff.line_ids:
            self.assertTrue(line.cutoff_amount == 100,
                            'SO line cutoff amount incorrect')

    def test_accrued_expense(self):
        """ Test partial po to process """
        # Removing all existing PO
        self.env.cr.execute('DELETE FROM purchase_order;')
        # Create PO
        self.products = [
            self.env.ref('product.product_delivery_01'),
            self.env.ref('product.product_delivery_02'),
        ]
        self.po = self.env['purchase.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'name': p.name,
                'product_id': p.id,
                'product_qty': 2.0,
                'product_uom': p.uom_po_id.id,
                'price_unit': 100.0,
                'date_planned': datetime.today().strftime(
                    DEFAULT_SERVER_DATETIME_FORMAT),
            }) for p in self.products],
        })

        type_cutoff = 'accrued_expense'
        cutoff = self.env['account.cutoff']\
            .with_context(default_type=type_cutoff)\
            .create({
                'type': type_cutoff,
                'company_id': 1,
                'cutoff_date': datetime.today() + relativedelta(days=+15),
            })
        cutoff.get_lines()
        self.assertTrue(
            len(cutoff.line_ids) == 0, 'There should be no po line to process')

        self.po.button_confirm()
        self.po.button_approve(force=True)
        pick = self.po.picking_ids[0]
        pick.force_assign()
        pick.pack_operation_product_ids.write({'qty_done': 1.0})
        wiz_act = pick.do_new_transfer()
        wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
        wiz.process()
        qties = [pol.qty_received for pol in self.po.order_line]
        self.assertEqual(
            qties, [1 for p in self.products],
            'Received quantities are wrong after partial reception')

        cutoff.get_lines()
        self.assertTrue(len(cutoff.line_ids) == 2,
                        '2 cutoff lines should be found')
        for line in cutoff.line_ids:
            self.assertTrue(line.cutoff_amount == -100,
                            'PO line cutoff amount incorrect')
