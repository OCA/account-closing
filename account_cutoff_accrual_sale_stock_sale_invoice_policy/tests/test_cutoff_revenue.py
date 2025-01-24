# Copyright 2025 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.account_cutoff_accrual_sale_stock.tests.test_cutoff_revenue import (
    TestAccountCutoffAccrualSaleStock,
)


class TestAccountCutoffAccrualSaleSaleInvoicePolicy(TestAccountCutoffAccrualSaleStock):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Make service product invoicable on delivery
        cls.env.ref("product.product_delivery_01").invoice_policy = "order"
        # but SO on order
        cls.so.invoice_policy = "delivery"
        # Re-run all tests from TestAccountCutoffAccrualSaleStock
        # we should have same result
