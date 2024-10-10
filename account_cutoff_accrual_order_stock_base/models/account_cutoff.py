# Copyright 2018 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import Command, api, fields, models
from odoo.tools import float_is_zero


class AccountCutoff(models.Model):
    _inherit = "account.cutoff"

    cutoff_account_prepaid_stock_id = fields.Many2one(
        comodel_name="account.account",
        string="Cut-off Prepaid Stock Account",
        domain="[('deprecated', '=', False)]",
        states={"done": [("readonly", True)]},
        check_company=True,
        tracking=True,
        default=lambda self: self._default_cutoff_account_prepaid_stock_id(),
        help="Account for accrual of prepaid stock expenses. "
        "For instance, goods invoiced and not yet received.",
    )

    @api.model
    def _default_cutoff_account_prepaid_stock_id(self):
        cutoff_type = self.env.context.get("default_cutoff_type")
        company = self.env.company
        if cutoff_type == "accrued_expense":
            account_id = company.default_prepaid_expense_account_id.id or False
        elif cutoff_type == "accrued_revenue":
            account_id = company.default_prepaid_revenue_account_id.id or False
        else:
            account_id = False
        return account_id

    def _prepare_counterpart_moves(
        self, to_provision, amount_total_pos, amount_total_neg
    ):
        if not self.cutoff_account_prepaid_stock_id:
            return super()._prepare_counterpart_moves(
                to_provision, amount_total_pos, amount_total_neg
            )
        if self.cutoff_type == "accrued_revenue":
            prepaid_amount = amount_total_neg
            amount = amount_total_pos
        elif self.cutoff_type == "accrued_expense":
            prepaid_amount = amount_total_pos
            amount = amount_total_neg
        else:
            prepaid_amount = 0
            amount = 0
        company_currency = self.company_id.currency_id
        cur_rprec = company_currency.rounding
        movelines_to_create = super()._prepare_counterpart_moves(
            to_provision, 0, amount
        )
        if not float_is_zero(prepaid_amount, precision_rounding=cur_rprec):
            movelines_to_create.append(
                Command.create(
                    {
                        "account_id": self.cutoff_account_prepaid_stock_id.id,
                        "debit": prepaid_amount,
                        "credit": 0,
                    },
                )
            )
        return movelines_to_create
