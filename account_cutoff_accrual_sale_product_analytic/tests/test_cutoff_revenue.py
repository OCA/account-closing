# Copyright 2025 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo.addons.account_cutoff_accrual_sale.tests.common import (
    TestAccountCutoffAccrualSaleCommon,
)


class TestAccountCutoffAccrualSale(TestAccountCutoffAccrualSaleCommon):
    def test_revenue_so_analytic_distribution(self):
        cutoff = self.revenue_cutoff
        self.so.action_confirm()
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff line should be found")
        for line in cutoff.line_ids:
            self.assertDictEqual(
                line.analytic_distribution,
                {str(self.analytic_account.id): self.price},
                "Analytic distribution is not correctly set",
            )
        cutoff.create_move()
        product_move_line = cutoff.move_id.line_ids.filtered("product_id")
        self.assertEqual(
            len(product_move_line), 1, "1 product move line should be found"
        )
        self.assertDictEqual(
            product_move_line.analytic_distribution,
            {str(self.analytic_account.id): 100},
            "Analytic distribution is not correctly set",
        )

    def test_revenue_product_analytic_distribution(self):
        cutoff = self.revenue_cutoff
        self.so.order_line.analytic_distribution = False
        analytic_account_2 = self.env["account.analytic.account"].create(
            {
                "name": "analytic_account 2",
                "plan_id": self.default_plan.id,
                "company_id": False,
            }
        )
        self.products.income_analytic_account_id = analytic_account_2
        self.so.action_confirm()
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 1, "1 cutoff line should be found")
        for line in cutoff.line_ids:
            self.assertFalse(
                line.analytic_distribution,
                "Analytic distribution is not correctly set",
            )
        cutoff.create_move()
        product_move_line = cutoff.move_id.line_ids.filtered("product_id")
        self.assertEqual(
            len(product_move_line), 1, "1 product move line should be found"
        )
        self.assertDictEqual(
            product_move_line.analytic_distribution,
            {str(analytic_account_2.id): 100},
            "Analytic distribution is not correctly set",
        )
