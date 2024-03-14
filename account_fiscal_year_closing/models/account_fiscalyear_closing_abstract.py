# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountFiscalyearClosingAbstract(models.AbstractModel):
    _name = "account.fiscalyear.closing.abstract"
    _description = "Account fiscalyear closing abstract"

    name = fields.Char(string="Description", required=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        ondelete="cascade",
    )
    check_draft_moves = fields.Boolean(
        string="Check draft moves",
        default=True,
        help="Checks that there are no draft moves on the fiscal year "
        "that is being closed. Non-confirmed moves won't be taken in "
        "account on the closing operations.",
    )


class AccountFiscalyearClosingConfigAbstract(models.AbstractModel):
    _name = "account.fiscalyear.closing.config.abstract"
    _description = "Account fiscalyear closing config abstract"
    _order = "sequence asc, id asc"

    name = fields.Char(string="Description", required=True)
    sequence = fields.Integer(index=True, default=1)
    code = fields.Char(string="Unique code", required=True)
    inverse = fields.Char(
        string="Inverse config",
        help="Configuration code to inverse its move",
    )
    move_type = fields.Selection(
        selection=[
            ("closing", "Closing"),
            ("opening", "Opening"),
            ("loss_profit", "Loss & Profit"),
            ("other", "Other"),
        ],
        string="Move type",
        default="closing",
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
    )
    closing_type_default = fields.Selection(
        selection=[
            ("balance", "Balance"),
            ("unreconciled", "Un-reconciled"),
        ],
        string="Default closing type",
        required=True,
        default="balance",
    )


class AccountFiscalyearClosingMappingAbstract(models.AbstractModel):
    _name = "account.fiscalyear.closing.mapping.abstract"
    _description = "Account fiscalyear closing mapping abstract"

    name = fields.Char(string="Description")


class AccountFiscalyearClosingTypeAbstract(models.AbstractModel):
    _name = "account.fiscalyear.closing.type.abstract"
    _description = "Account fiscalyear closing type abstract"

    closing_type = fields.Selection(
        selection=[
            ("balance", "Balance"),
            ("unreconciled", "Un-reconciled"),
        ],
        string="Default closing type",
        required=True,
        default="unreconciled",
    )
    account_type = fields.Selection(
        selection=[
            ("asset_receivable", "Receivable"),
            ("asset_cash", "Bank and Cash"),
            ("asset_current", "Current Assets"),
            ("asset_non_current", "Non-current Assets"),
            ("asset_prepayments", "Prepayments"),
            ("asset_fixed", "Fixed Assets"),
            ("liability_payable", "Payable"),
            ("liability_credit_card", "Credit Card"),
            ("liability_current", "Current Liabilities"),
            ("liability_non_current", "Non-current Liabilities"),
            ("equity", "Equity"),
            ("equity_unaffected", "Current Year Earnings"),
            ("income", "Income"),
            ("income_other", "Other Income"),
            ("expense", "Expenses"),
            ("expense_depreciation", "Depreciation"),
            ("expense_direct_cost", "Cost of Revenue"),
            ("off_balance", "Off-Balance Sheet"),
        ],
        string="Type",
        required=True,
    )
