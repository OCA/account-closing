# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    revenue_cutoff_journal_id = fields.Many2one(
        related="company_id.revenue_cutoff_journal_id",
        readonly=False,
        string="Revenue cut-off journal",
    )
    expense_cutoff_journal_id = fields.Many2one(
        related="company_id.expense_cutoff_journal_id",
        readonly=False,
        string="Expense cut-off journal",
    )
    link_product = fields.Boolean(
        "Link product",
        config_parameter="account_move_cutoff.link_product",
        help="Link product on deferred account.move.line.",
    )
    default_cutoff_method = fields.Selection(
        [
            ("equal", "Equal"),
            ("monthly_prorata_temporis", "Prorata temporis (by month %)"),
        ],
        string="Default Cutoff method",
        default="monthly_prorata_temporis",
        default_model="account.move.line",
        required=True,
        help=(
            "Determine how to split amounts over periods:\n"
            " * Equal: same amount is splitted over periods of the service"
            "   (using start and end date on the invoice line).\n"
            " * Prorata temporis by month %: amount is splitted over"
            "   the rate of service days in the month.\n"
        ),
    )
