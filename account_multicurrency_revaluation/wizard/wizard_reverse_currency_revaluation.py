# Copyright 2022 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, exceptions, fields, models


class WizardCurrencyRevaluation(models.TransientModel):
    _name = "wizard.reverse.currency.revaluation"
    _description = "Reverse Currency Revaluation Wizard"

    @api.model
    def _get_default_journal_id(self):
        return self.env.company.currency_reval_journal_id

    revaluation_interval_start_date = fields.Date(
        string="Revaluation Start Date",
        help="All entries revaluated on or after this date will be taken into account.",
    )
    revaluation_interval_end_date = fields.Date(
        string="Revaluation End Date",
        help="All entries revaluated on or before this date will be taken into account.",
    )

    reverse_posting_date = fields.Date(
        string="Reverse Entries Accounting Date",
        help="Date that will be assigned to the reverse entries created.",
    )

    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        domain=[("type", "=", "general")],
        help="You can set the default journal in company settings.",
        required=True,
        default=lambda self: self._get_default_journal_id(),
    )

    entries_to_reverse_ids = fields.Many2many(
        comodel_name="account.move",
        string="Entries to reverse",
        help="The revaluated entries that will be reversed.",
    )

    @api.onchange("revaluation_interval_start_date", "revaluation_interval_end_date")
    def onchange_revaluation_interval_dates(self):
        self.ensure_one()
        account_move_model = self.env["account.move"]
        company_id = self.journal_id.company_id.id or self.env.company.id
        domain = [
            ("revaluation_to_reverse", "=", True),
            ("state", "=", "posted"),
            ("company_id", "=", company_id),
        ]
        if self.revaluation_interval_start_date:
            domain += [("date", ">=", self.revaluation_interval_start_date)]
        if self.revaluation_interval_end_date:
            domain += [("date", "<=", self.revaluation_interval_end_date)]
        entries = account_move_model.search(domain)
        final_entries = account_move_model
        for entry in entries:
            reverse_entry = account_move_model.search(
                [("reversed_entry_id", "=", entry.id)], limit=1
            )
            if not reverse_entry:
                final_entries += entry
        self.entries_to_reverse_ids = final_entries

    def reverse_revaluate_currency(self):
        entries = self.entries_to_reverse_ids
        created_entries = entries._reverse_moves()
        vals = {"revaluation_reversed": True, "revaluation_to_reverse": False}
        if self.reverse_posting_date:
            vals.update({"date": self.reverse_posting_date})
        created_entries.write(vals)
        if self.journal_id.company_id.auto_post_entries:
            for entry in created_entries:
                entry.post()
        # Mark entries reversed as not to be reversed anymore
        entries.write({"revaluation_to_reverse": False})
        if created_entries:
            return {
                "domain": [("id", "in", created_entries.ids)],
                "name": _("Reverse Revaluation Entries"),
                "view_mode": "tree,form",
                "auto_search": True,
                "res_model": "account.move",
                "view_id": False,
                "search_view_id": False,
                "type": "ir.actions.act_window",
            }
        else:
            raise exceptions.Warning(_("No accounting entry has been posted."))
