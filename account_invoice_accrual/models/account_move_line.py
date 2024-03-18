# Copyright 2017 ACSONE SA/NV
# Copyright 2018 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_accrual_move_line_vals(self, move_line_prefix):
        res = []
        accrual_taxes = self.company_id.accrual_taxes
        for line in self:
            name = line.name
            if move_line_prefix:
                name = " ".join([move_line_prefix, name])
            vals = {
                "date_maturity": line.date_maturity,
                "partner_id": line.partner_id.id,
                "debit": line.debit,
                "credit": line.credit,
                "name": name,
                "account_id": line.account_id.id,
                "analytic_distribution": line.analytic_distribution,
                "amount_currency": line.amount_currency,
                "currency_id": line.currency_id.id,
                "quantity": line.quantity,
                "product_id": line.product_id.id,
                "product_uom_id": line.product_uom_id.id,
            }
            if accrual_taxes:
                vals["tax_ids"] = [Command.set(line.tax_ids.ids)]
            res.append(vals)
        return res
