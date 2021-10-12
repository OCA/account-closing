# -*- coding: utf-8 -*-
# Copyright 2021 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.account_cutoff_accrual_picking.tests.test_accrual_orders import (
    TestAccountCutoffAccrualPicking,
)


class TestAccountCutoffAccrualPickingAnalytic(TestAccountCutoffAccrualPicking):
    def setUp(self):
        super(TestAccountCutoffAccrualPickingAnalytic, self).setUp()
        self.analytic_account1 = self.env["account.analytic.account"].create(
            {"name": "test analytic_account1"}
        )
        self.analytic_account2 = self.env["account.analytic.account"].create(
            {"name": "test analytic_account2"}
        )
        self.products.with_context(force_company=self.env.user.company_id.id).write(
            {
                "income_analytic_account_id": self.analytic_account1.id,
                "expense_analytic_account_id": self.analytic_account2.id,
            }
        )

    def test_analytic_expense(self):
        cutoff = self.expense_cutoff
        analytic = cutoff._get_expense_analytic(self.po.order_line[0])
        self.assertEqual(
            analytic,
            self.analytic_account2,
        )

    def test_analytic_revenue(self):
        cutoff = self.revenue_cutoff
        analytic = cutoff._get_revenue_analytic(self.so.order_line[0])
        self.assertEqual(
            analytic,
            self.analytic_account1,
        )
