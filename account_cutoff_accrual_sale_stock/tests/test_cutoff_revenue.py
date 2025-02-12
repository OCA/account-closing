# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from .common import TestAccountCutoffAccrualSaleStockCommon


class TestAccountCutoffAccrualSaleStock(TestAccountCutoffAccrualSaleStockCommon):
    def test_accrued_revenue_empty(self):
        """Test cutoff when there is no SO."""
        cutoff = self.revenue_cutoff
        cutoff.get_lines()
        self.assertEqual(
            len(cutoff.line_ids), 0, "There should be no SO line to process"
        )

    def test_revenue_analytic_distribution(self):
        cutoff = self.revenue_cutoff
        self._confirm_so_and_do_picking(2)
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertDictEqual(
                line.analytic_distribution,
                {str(self.analytic_account.id): 100.0},
                "Analytic distribution is not correctly set",
            )

    def test_revenue_tax_line(self):
        cutoff = self.revenue_cutoff
        self._confirm_so_and_do_picking(2)
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids.filtered(
            lambda l: l.product_id.detailed_type == "product"
        ):
            self.assertEqual(
                len(line.tax_line_ids), 1, "tax lines is not correctly set"
            )
            self.assertEqual(line.tax_line_ids.cutoff_account_id, self.cutoff_account)
            self.assertEqual(line.tax_line_ids.tax_id, self.tax_sale)
            self.assertEqual(line.tax_line_ids.base, 200)
            self.assertEqual(line.tax_line_ids.amount, 30)
            self.assertEqual(line.tax_line_ids.cutoff_amount, 30)
