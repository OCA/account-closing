# -*- coding: utf-8 -*-
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tests.common import TransactionCase


class TestAccountCutoffAccrualPicking(TransactionCase):

    def setUp(self):
        super(TestAccountCutoffAccrualPicking, self).setUp()
        self.products = {
            'prod_order': self.env.ref('product.product_order_01'),
            'prod_del': self.env.ref('product.product_delivery_01'),
            'serv_order': self.env.ref('product.service_order_01'),
            'serv_del': self.env.ref('product.service_delivery'),
        }
        self.partner = self.env.ref('base.res_partner_1')
        # Removing all existing sale orders and add one we want to test
        self.env.cr.execute('DELETE FROM sale_order;')
        self.so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0,
                            {'name': p.name, 'product_id': p.id,
                             'product_uom_qty': 2, 'product_uom': p.uom_id.id,
                             'price_unit': p.list_price})
                           for (_, p) in self.products.iteritems()],
            'pricelist_id': self.env.ref('product.list0').id,
        })
        self.product_id_1 = self.env.ref('product.product_product_8')
        po_vals = {
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_id_1.name,
                    'product_id': self.product_id_1.id,
                    'product_qty': 5.0,
                    'product_uom': self.product_id_1.uom_po_id.id,
                    'price_unit': 500.0,
                    'date_planned': datetime.today().strftime(
                        DEFAULT_SERVER_DATETIME_FORMAT),
                })],
        }
        # Removing all existing purchase orders and add one to test
        self.env.cr.execute('DELETE FROM purchase_order;')
        self.po = self.env['purchase.order'].create(po_vals)

    def test_accrued_revenue_nothing_todo(self):
        """ Test no sale order line to process"""
        cutoff = self.env['account.cutoff'].create({
            'type': 'accrued_revenue',
            'company_id': 1
        })
        r = cutoff.get_lines_for_cutoff()
        self.assertTrue(len(r) == 0, 'There should be no so line to process')

    def test_accrued_expense_nothing_todo(self):
        """ Test no purchase order line to process"""
        cutoff = self.env['account.cutoff'].create({
            'type': 'accrued_expense',
            'company_id': 1
        })
        r = cutoff.get_lines_for_cutoff()
        self.assertTrue(len(r) == 0, 'There should be no po line to process')

    def test_accrued_revenue(self):
        """ Test complete so to process"""
        cutoff = self.env['account.cutoff'].create({
            'type': 'accrued_revenue',
            'company_id': 1
        })
        self.so.action_confirm()
        lines = cutoff.get_lines_for_cutoff()
        self.assertTrue(len(lines) == 2,
                        '2 lines should be found to calculate cutoff')
        l = cutoff._prepare_line(lines[0])
        self.assertTrue(l['cutoff_amount'] == 560,
                        'So line 0 cutoff amount incorrect')
        l = cutoff._prepare_line(lines[1])
        self.assertTrue(l['cutoff_amount'] == 180,
                        'So line 1 cutoff amount incorrect')

    def test_accrued_expense(self):
        """ Test partial po to process """
        cutoff = self.env['account.cutoff'].create({
            'type': 'accrued_expense',
            'company_id': 1
        })
        # Confirm po and validate shipment
        self.po.button_confirm()
        self.po.button_approve(force=True)
        pick = self.po.picking_ids[0]
        pick.force_assign()
        pick.pack_operation_product_ids[0].write({'qty_done': 4.0})
        wiz_act = pick.do_new_transfer()
        wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
        wiz.process()
        lines = cutoff.get_lines_for_cutoff()
        self.assertTrue(len(lines) == 1,
                        '1 lines should be found to calculate expense cutoff')
        l = cutoff._prepare_line(lines[0])
        self.assertTrue(l['cutoff_amount'] == -2000,
                        'Line 0 cutoff amount incorrect')
