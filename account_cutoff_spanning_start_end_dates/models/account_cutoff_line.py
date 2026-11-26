# Copyright 2026 Lorenzo Battistini
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountCutoffLine(models.Model):
    _inherit = "account.cutoff.line"

    is_spanning = fields.Boolean(
        string="Spanning",
        compute="_compute_is_spanning",
        store=True,
        help="The period of this accrual line ends after the cut-off date, "
        "so only a part of its amount is accrued.",
    )

    @api.depends("end_date", "parent_id.cutoff_date", "parent_id.cutoff_type")
    def _compute_is_spanning(self):
        for line in self:
            cutoff = line.parent_id
            line.is_spanning = bool(
                cutoff.cutoff_type in ("accrued_expense", "accrued_revenue")
                and line.end_date
                and cutoff.cutoff_date
                and line.end_date > cutoff.cutoff_date
            )
