# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.addons.account_cutoff_picking.tests.test_cutoff_revenue import (
    AccountCutoffCutoffRevenueCommon,
)


class TestAccountCutoffPickingCategory(AccountCutoffCutoffRevenueCommon):
    def test_category(self):
        # Create SO and pickings, then create cutoff
        # Then create the cutoff move
        # Result lines should contains the products category
        cutoff = self.revenue_cutoff
        self._confirm_so_and_do_picking(2)
        cutoff.get_lines()
        self.assertEqual(len(cutoff.line_ids), 2, "2 cutoff lines should be found")
        for line in cutoff.line_ids:
            self.assertEqual(
                line.cutoff_amount, 100 * 2, "SO line cutoff amount incorrect"
            )
        action = cutoff.create_move()
        move = self.env["account.move"].browse(action.get("res_id"))
        self.assertEqual(move.line_ids.categ_id, self.products.categ_id)
