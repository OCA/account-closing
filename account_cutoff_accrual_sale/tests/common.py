# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command, fields

from odoo.addons.account_cutoff_accrual_order_base.tests.common import (
    TestAccountCutoffAccrualOrderCommon,
)


class TestAccountCutoffAccrualSaleCommon(TestAccountCutoffAccrualOrderCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tax_sale = cls.env.company.account_sale_tax_id
        cls.cutoff_account = cls.env["account.account"].create(
            {
                "name": "account accrued revenue",
                "code": "accountAccruedExpense",
                "account_type": "asset_current",
                "company_id": cls.env.company.id,
            }
        )
        cls.tax_sale.account_accrued_revenue_id = cls.cutoff_account
        # Removing all existing SO
        cls.env.cr.execute("DELETE FROM sale_order;")
        # Make service product invoicable on order
        cls.env.ref("product.expense_product").invoice_policy = "order"
        # Create SO and confirm
        cls.price = 100
        cls.qty = 5
        cls.so = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "partner_invoice_id": cls.partner.id,
                "partner_shipping_id": cls.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "name": p.name,
                            "product_id": p.id,
                            "product_uom_qty": cls.qty,
                            "product_uom": p.uom_id.id,
                            "price_unit": cls.price,
                            "analytic_distribution": {
                                str(cls.analytic_account.id): 100.0
                            },
                            "tax_id": [Command.set(cls.tax_sale.ids)],
                        },
                    )
                    for p in cls.products
                ],
                "pricelist_id": cls.env.ref("product.list0").id,
            }
        )
        # Create cutoff
        type_cutoff = "accrued_revenue"
        cls.revenue_cutoff = (
            cls.env["account.cutoff"]
            .with_context(default_cutoff_type=type_cutoff)
            .create(
                {
                    "cutoff_type": type_cutoff,
                    "order_line_model": "sale.order.line",
                    "company_id": 1,
                    "cutoff_date": fields.Date.today(),
                }
            )
        )
