# Copyright 2023 Foodles (http://www.foodles.co).
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class Account(models.Model):
    _inherit = "account.account"

    deferred_accrual_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Revenue/Expense accrual account",
        domain="[('company_id', '=', company_id),"
        "('internal_type', 'not in', ('receivable', 'payable')),"
        "('is_off_balance', '=', False)]",
        help=(
            "Account used to deferred Revenues/Expenses in next periods. "
            "If not set revenue won't be deferred"
        ),
    )
