# Copyright 2013-2020 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class AccountCutOff(models.Model):
    _inherit = "account.cutoff"

    @api.model
    def _default_cutoff_account_id(self):
        account_id = super()._default_cutoff_account_id()
        cutoff_type = self.env.context.get("cutoff_type")
        company = self.env.company
        if cutoff_type == "accrued_expense":
            account_id = company.default_accrued_expense_account_id.id or False
        elif cutoff_type == "accrued_revenue":
            account_id = company.default_accrued_revenue_account_id.id or False
        return account_id

    def _prepare_tax_lines(self, tax_compute_all_res, currency):
        res = []
        ato = self.env["account.tax"]
        company_currency = self.company_id.currency_id
        cur_rprec = company_currency.rounding
        for tax_line in tax_compute_all_res["taxes"]:
            tax = ato.browse(tax_line["id"])
            if float_is_zero(tax_line["amount"], precision_rounding=cur_rprec):
                continue
            if self.cutoff_type == "accrued_expense":
                tax_accrual_account_id = tax.account_accrued_expense_id.id
                tax_account_field_label = _("Accrued Expense Tax Account")
            elif self.cutoff_type == "accrued_revenue":
                tax_accrual_account_id = tax.account_accrued_revenue_id.id
                tax_account_field_label = _("Accrued Revenue Tax Account")
            if not tax_accrual_account_id:
                raise UserError(
                    _("Missing '%s' on tax '%s'.")
                    % (tax_account_field_label, tax.display_name)
                )
            tax_amount = currency.round(tax_line["amount"])
            tax_accrual_amount = currency._convert(
                tax_amount, company_currency, self.company_id, self.cutoff_date
            )
            res.append(
                (
                    0,
                    0,
                    {
                        "tax_id": tax_line["id"],
                        "base": tax_line["base"],  # in currency
                        "amount": tax_amount,  # in currency
                        "sequence": tax_line["sequence"],
                        "cutoff_account_id": tax_accrual_account_id,
                        "cutoff_amount": tax_accrual_amount,  # in company currency
                    },
                )
            )
        return res


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
