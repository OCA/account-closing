# Copyright 2023 Foodles (http://www.foodles.co).
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "cutoff.period.mixin"]

    cutoff_from_id = fields.Many2one(
        comodel_name="account.move",
        string="Cut-off source entry",
        help="Source entry that generate the current deferred revenue/expense entry",
    )
    cutoff_move_count = fields.Integer(compute="_compute_cutoff_move_count")

    cutoff_entry_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="cutoff_from_id",
        string="Cut-off entries",
        readonly=True,
        help=(
            "Field use to make easy to user to follow entries generated "
            "from this specific entry to deferred revenues or expenses."
        ),
    )

    def _compute_cutoff_move_count(self):
        for rec in self:
            rec.cutoff_move_count = len(rec.cutoff_entry_ids)

    def button_draft(self):
        res = super().button_draft()
        # it's probably a bit ugly, for time being I prefer to unlink/create
        # to maintain consistency cutoff_entry_ids shouldn't be on sale/purchase
        # journals
        self.cutoff_entry_ids.line_ids.remove_move_reconcile()
        # force delete because we shouldn't remove entries that has been posted
        self.cutoff_entry_ids.with_context(force_delete=True).unlink()
        return res

    def action_post(self):
        result = super().action_post()
        for move, lines in self._get_deferrable_lines():
            move._create_cutoff_entries(lines)

        return result

    def _get_deferrable_lines(self):
        """Return line to deferred revenues/expenses group by move"""
        return (
            self.filtered(lambda account_move: account_move.move_type != "entry")
            .line_ids.filtered(lambda line: line.is_deferrable_line)
            .group_recordset_by(lambda move_line: move_line.move_id)
        )

    def _get_deferred_periods(self, lines):
        """Generate periods concerned by given lines from min and max date

        This implementation consider a month as period, each period
        is represented by a datetime.date: the first day of the month
        """
        self.ensure_one()
        first_date = self.date
        last_date = max([first_date] + lines.mapped("end_date"))
        return self._generate_monthly_periods(first_date, last_date)

    def _get_deferred_date_from_period(self, period):
        # as today we only support monthly period represented by
        # the first date
        return period

    def _get_deferred_journal(self):
        self.ensure_one()
        # At the moment we handle only deferred entries from
        # Sale and Purchase journal
        journal = self.env["account.journal"].browse()
        if self.journal_id.type == "sale":
            journal = self.company_id.revenue_cutoff_journal_id
        elif self.journal_id.type == "purchase":
            journal = self.company_id.expense_cutoff_journal_id
        return journal

    def _get_deferred_titles(self):
        self.ensure_one()
        cutoff_title = _("Advance recognition of %s (%s)") % (
            self.name,
            self.date.strftime("%m %Y"),
        )
        deferred_title = _("Advance adjustment of %s (%s)") % (
            self.name,
            self.date.strftime("%m %Y"),
        )
        if self.journal_id.type == "sale":
            cutoff_title = _("Advance revenue recognition of %s (%s)") % (
                self.name,
                self.date.strftime("%m %Y"),
            )
            deferred_title = _("Advance revenue adjustment of %s (%s)") % (
                self.name,
                self.date.strftime("%m %Y"),
            )
        elif self.journal_id.type == "purchase":
            cutoff_title = _("Advance expense recognition of %s (%s)") % (
                self.name,
                self.date.strftime("%m %Y"),
            )
            deferred_title = _("Advance expense adjustment of %s (%s)") % (
                self.name,
                self.date.strftime("%m %Y"),
            )
        return cutoff_title, deferred_title

    def _prepare_deferred_entry(self, journal, date_, reference):
        return {
            "currency_id": journal.currency_id.id or journal.company_id.currency_id.id,
            "move_type": "entry",
            "line_ids": [],
            "ref": reference,
            "date": date_,
            "journal_id": journal.id,
            "partner_id": self.partner_id.id,
            "cutoff_from_id": self.id,
        }

    def _create_cutoff_entries(self, lines_to_deferred):
        # create one entry to move to the deferred_accrual_account_id
        self.ensure_one()

        entries = self.env["account.move"]
        journal = self._get_deferred_journal()
        # if not journal returns means no deferred entries to
        # generate, we don't want any raises here
        if not journal:
            return

        cutoff_title, deferred_title = self._get_deferred_titles()
        periods = self._get_deferred_periods(lines_to_deferred)
        cutoff_entry = self.create(
            self._prepare_deferred_entry(
                journal, fields.Date.to_string(self.date), cutoff_title
            )
        )
        entries |= cutoff_entry

        amounts = self._get_amounts_by_period(lines_to_deferred, periods)
        # manage cutoff entry
        for line, amounts_by_period in amounts:
            line._create_cutoff_entry_lines(
                cutoff_entry,
                periods[0],
                sum([amounts_by_period.get(p, 0) for p in periods[1:]]),
            )

        # manage deferred entries
        for period in periods[1:]:
            deferred_entry = self.create(
                self._prepare_deferred_entry(
                    journal,
                    fields.Date.to_string(self._get_deferred_date_from_period(period)),
                    deferred_title,
                )
            )
            for line, amounts_by_period in amounts:
                if self.currency_id.is_zero(amounts_by_period.get(period, 0)):
                    continue

                line._create_deferred_entry_lines(
                    deferred_entry, period, amounts_by_period[period]
                )

            if deferred_entry.line_ids:
                entries |= deferred_entry
            else:
                # TODO: not sure if the case is possible
                # if so not sure it's good idea to create and unlink
                # in such transaction
                deferred_entry.unlink()

        entries.action_post()
        for _account, lines in entries.line_ids.filtered(
            lambda line: line.account_id.reconcile
            and not line.currency_id.is_zero(line.balance)
        ).group_recordset_by(lambda line: line.account_id):
            lines.reconcile()

    def _get_amounts_by_period(self, lines_to_deferred, periods):
        """return data with amount to dispatched per account move line and per periods::

            [
                (
                    line1, # record of the original account.move.line,
                    { # dict of amounts per period
                        period1: amount1,
                        period2: amount2,
                    }
                ),
                (
                    line2,
                    {...}
                )
            ]

        Developer should take care of rounding issues.

        amount on the first period is the amount that won't be deferred
        """
        return lines_to_deferred._get_deferred_amounts_by_period(periods)

    def action_view_deferred_entries(self):
        self.ensure_one()
        xmlid = "account.action_move_journal_line"
        action = self.env["ir.actions.act_window"]._for_xml_id(xmlid)
        action["domain"] = [("id", "in", self.cutoff_entry_ids.ids)]
        return action
