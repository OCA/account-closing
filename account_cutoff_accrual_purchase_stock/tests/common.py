# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.tests.common import Form

from odoo.addons.account_cutoff_accrual_order_base.tests.common import (
    TestAccountCutoffAccrualOrderCommon,
)


class TestAccountCutoffAccrualPurchaseCommon(TestAccountCutoffAccrualOrderCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Removing all existing PO
        cls.env.cr.execute("DELETE FROM purchase_order;")
        # Create PO
        cls.tax_purchase = cls.env.company.account_purchase_tax_id
        cls.cutoff_account = cls.env["account.account"].create(
            {
                "name": "account accrued expense",
                "code": "accountAccruedExpense",
                "account_type": "asset_current",
                "company_id": cls.env.company.id,
            }
        )
        cls.tax_purchase.account_accrued_expense_id = cls.cutoff_account
        cls.po = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "name": p.name,
                            "product_id": p.id,
                            "product_qty": 5,
                            "product_uom": p.uom_po_id.id,
                            "price_unit": 100,
                            "date_planned": fields.Date.to_string(
                                datetime.today() + relativedelta(days=-15)
                            ),
                            "analytic_distribution": {
                                str(cls.analytic_account.id): 100.0
                            },
                            "taxes_id": [Command.set(cls.tax_purchase.ids)],
                        },
                    )
                    for p in cls.products
                ],
            }
        )
        type_cutoff = "accrued_expense"
        cls.expense_cutoff = (
            cls.env["account.cutoff"]
            .with_context(default_cutoff_type=type_cutoff)
            .create(
                {
                    "cutoff_type": type_cutoff,
                    "order_line_model": "purchase.order.line",
                    "company_id": 1,
                    "cutoff_date": fields.Date.today(),
                }
            )
        )

    def _confirm_po_and_do_picking(self, qty_done):
        self.po.button_confirm()
        self.po.button_approve(force=True)
        pick = self.po.picking_ids
        pick.action_assign()
        pick.move_line_ids.write({"qty_done": qty_done})
        pick._action_done()
        qties = [pol.qty_received for pol in self.po.order_line]
        self.assertEqual(
            qties,
            [qty_done if p.detailed_type == "product" else 0 for p in self.products],
            "Delivered quantities are wrong after partial delivery",
        )

    def _create_po_invoice(self, date):
        invoice_form = Form(
            self.env["account.move"].with_context(
                default_move_type="in_invoice", default_purchase_id=self.po.id
            )
        )
        invoice_form.invoice_date = date
        return invoice_form.save()
