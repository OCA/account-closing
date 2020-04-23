# Copyright 2013-2020 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountCutOff(models.Model):
    _inherit = "account.cutoff"

    @api.model
    def _default_cutoff_account_id(self):
        account_id = super()._default_cutoff_account_id()
        cutoff_type = self.env.context.get("cutoff_type")
        company = self.env.user.company_id
        if cutoff_type == "accrued_expense":
            account_id = company.default_accrued_expense_account_id.id or False
        elif cutoff_type == "accrued_revenue":
            account_id = company.default_accrued_revenue_account_id.id or False
        return account_id


class AccountCutoffLine(models.Model):
    _inherit = "account.cutoff.line"

    quantity = fields.Float(
        string="Quantity", digits="Product Unit of Measure", readonly=True
    )
    price_unit = fields.Float(
        string="Unit Price",
        digits="Product Price",
        readonly=True,
        help="Price per unit (discount included) in the default unit of "
        "measure of the product in the currency of the 'Currency' field.",
    )
    price_origin = fields.Char(readonly=True)
