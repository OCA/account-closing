# Copyright 2026 Lorenzo Battistini
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models


class AccountCutoff(models.Model):
    _inherit = "account.cutoff"

    cutoff_account_spanning_id = fields.Many2one(
        comodel_name="account.account",
        string="Cut-off Spanning Account",
        domain="[('deprecated', '=', False), ('company_ids', 'in', company_id)]",
        compute="_compute_cutoff_account_spanning_id",
        store=True,
        readonly=False,
        precompute=True,
        check_company=True,
        tracking=True,
        help="Account for the accrual lines whose period spans the cut-off date. "
        "If empty, the cut-off account is used for all the lines.",
    )

    @api.depends("company_id", "cutoff_type")
    def _compute_cutoff_account_spanning_id(self):
        for rec in self:
            company = rec.company_id
            if rec.cutoff_type == "accrued_expense":
                account = company.default_accrued_expense_spanning_account_id
            elif rec.cutoff_type == "accrued_revenue":
                account = company.default_accrued_revenue_spanning_account_id
            else:
                account = self.env["account.account"]
            rec.cutoff_account_spanning_id = account

    def _prepare_counterpart_moves(self, to_provision, amount_total):
        if not self.cutoff_account_spanning_id:
            return super()._prepare_counterpart_moves(to_provision, amount_total)
        currency = self.company_currency_id
        spanning_lines = self.line_ids.filtered("is_spanning")
        spanning_amount = currency.round(
            sum(spanning_lines.mapped("cutoff_amount"))
            + sum(spanning_lines.tax_line_ids.mapped("cutoff_amount"))
        )
        res = []
        if not currency.is_zero(amount_total - spanning_amount):
            res += super()._prepare_counterpart_moves(
                to_provision, amount_total - spanning_amount
            )
        if not currency.is_zero(spanning_amount):
            # provision amounts < 0 are debits, so their counterpart is a credit
            res.append(
                Command.create(
                    {
                        "account_id": self.cutoff_account_spanning_id.id,
                        "debit": max(spanning_amount, 0),
                        "credit": max(-spanning_amount, 0),
                    },
                )
            )
        return res
