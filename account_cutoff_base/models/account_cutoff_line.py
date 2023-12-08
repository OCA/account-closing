# Copyright 2013-2021 Akretion (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountCutoffLine(models.Model):
    _name = "account.cutoff.line"
    _inherit = "analytic.mixin"
    _check_company_auto = True
    _description = "Account Cut-off Line"

    parent_id = fields.Many2one("account.cutoff", string="Cut-off", ondelete="cascade")
    cutoff_type = fields.Selection(related="parent_id.cutoff_type")
    company_id = fields.Many2one(
        "res.company", related="parent_id.company_id", store=True
    )
    name = fields.Char("Description")
    company_currency_id = fields.Many2one(
        related="parent_id.company_currency_id",
        string="Company Currency",
    )
    partner_id = fields.Many2one("res.partner", string="Partner", readonly=True)
    quantity = fields.Float(digits="Product Unit of Measure", readonly=True)
    price_unit = fields.Float(
        string="Unit Price w/o Tax",
        digits="Product Price",
        readonly=True,
        help="Price per unit (discount included) without taxes in the default "
        "unit of measure of the product in the currency of the 'Currency' field.",
    )
    price_origin = fields.Char(readonly=True)
    origin_move_line_id = fields.Many2one(
        "account.move.line", string="Origin Journal Item", readonly=True
    )
    origin_move_id = fields.Many2one(
        related="origin_move_line_id.move_id", string="Origin Journal Entry"
    )
    origin_move_date = fields.Date(
        related="origin_move_line_id.move_id.date", string="Origin Journal Entry Date"
    )
    account_id = fields.Many2one(
        "account.account",
        "Account",
        required=True,
        readonly=True,
        check_company=True,
    )
    cutoff_account_id = fields.Many2one(
        "account.account",
        string="Cut-off Account",
        required=True,
        readonly=True,
        check_company=True,
    )
    cutoff_account_code = fields.Char(
        related="cutoff_account_id.code", string="Cut-off Account Code"
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        readonly=True,
    )
    amount = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
        help="Amount that is used as base to compute the Cut-off Amount.",
    )
    cutoff_amount = fields.Monetary(
        string="Cut-off Amount",
        currency_field="company_currency_id",
        readonly=True,
        help="Cut-off Amount without taxes in the Company Currency.",
    )
    tax_line_ids = fields.One2many(
        "account.cutoff.tax.line",
        "parent_id",
        string="Cut-off Tax Lines",
        readonly=True,
    )
    notes = fields.Text()
