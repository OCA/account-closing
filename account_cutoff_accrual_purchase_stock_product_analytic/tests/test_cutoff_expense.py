# Copyright 2025 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo.addons.account_cutoff_accrual_purchase_stock.tests.common import (
    TestAccountCutoffAccrualPurchaseStockCommon,
)


class TestAccountCutoffAccrualPurchaseStockProductAnalytic(
    TestAccountCutoffAccrualPurchaseStockCommon
):
    def test_revenue_po_analytic_distribution(self):
        cutoff = self.expense_cutoff
        self._confirm_po_and_do_picking(2)
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff line should be found")
        for line in cutoff.line_ids:
            self.assertDictEqual(
                line.analytic_distribution,
                {str(self.analytic_account.id): self.price},
                "Analytic distribution is not correctly set",
            )
        cutoff.create_move()
        product_move_line = cutoff.move_id.line_ids.filtered("product_id")
        self.assertEqual(
            len(product_move_line), 2, "2 product move line should be found"
        )
        for line in product_move_line:
            self.assertDictEqual(
                line.analytic_distribution,
                {str(self.analytic_account.id): 100},
                "Analytic distribution is not correctly set",
            )

    def test_revenue_product_analytic_distribution(self):
        cutoff = self.expense_cutoff
        self.po.order_line.analytic_distribution = False
        analytic_account_2 = self.env["account.analytic.account"].create(
            {
                "name": "analytic_account 2",
                "plan_id": self.default_plan.id,
                "company_id": False,
            }
        )
        self.products.expense_analytic_account_id = analytic_account_2
        self._confirm_po_and_do_picking(2)
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff line should be found")
        for line in cutoff.line_ids:
            self.assertFalse(
                line.analytic_distribution,
                "Analytic distribution is not correctly set",
            )
        cutoff.create_move()
        product_move_line = cutoff.move_id.line_ids.filtered("product_id")
        self.assertEqual(
            len(product_move_line), 2, "2 product move line should be found"
        )
        for line in product_move_line:
            self.assertDictEqual(
                line.analytic_distribution,
                {str(analytic_account_2.id): 100},
                "Analytic distribution is not correctly set",
            )
