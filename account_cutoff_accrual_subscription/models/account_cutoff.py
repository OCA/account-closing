# Copyright 2019-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import date_utils
from odoo.tools.misc import format_amount, format_date


class AccountCutoff(models.Model):
    _inherit = "account.cutoff"

    def get_lines(self):
        res = super().get_lines()
        if self.cutoff_type not in ["accrued_expense", "accrued_revenue"]:
            return res

        line_obj = self.env["account.cutoff.line"]
        sub_obj = self.env["account.cutoff.accrual.subscription"]

        fy_start_date, fy_end_date = date_utils.get_fiscal_year(
            self.cutoff_date,
            day=self.company_id.fiscalyear_last_day,
            month=int(self.company_id.fiscalyear_last_month),
        )
        if not fy_start_date:
            raise UserError(_("Odoo cannot compute the fiscal year start date."))

        type2subtype = {
            "accrued_expense": "expense",
            "accrued_revenue": "revenue",
        }
        sub_type = type2subtype[self.cutoff_type]
        sign = sub_type == "revenue" and -1 or 1
        subs = sub_obj.search(
            [
                ("company_id", "=", self.company_id.id),
                ("subscription_type", "=", sub_type),
                ("start_date", "<=", self.cutoff_date),
            ]
        )
        if subs:
            # check that the cutoff is the last day of a month
            # otherwise, we have pb with when we compute intervals
            # with cutoff date is a day which is not present for all months
            last_day_same_month = self.cutoff_date + relativedelta(day=31)
            if last_day_same_month.day != self.cutoff_date.day:
                raise UserError(
                    _(
                        "The cutoffs with subscription only work when the cutoff "
                        "date (%s) is the last day of a month."
                    )
                    % format_date(self.env, self.cutoff_date)
                )
            if not self.source_journal_ids:
                raise UserError(_("Missing source journals."))
            self.message_post(
                body=_("Computing provisions from %d subscriptions.") % len(subs)
            )
        common_domain = [("journal_id", "in", self.source_journal_ids.ids)]
        if self.source_move_state == "posted":
            common_domain.append(("parent_state", "=", "posted"))
        else:
            common_domain.append(("parent_state", "in", ("draft", "posted")))
        work = {}
        # Generate time intervals and compute existing expenses/revenue
        for sub in subs:
            sub._process_subscription(
                work, fy_start_date, self.cutoff_date, common_domain, sign
            )
        # Create mapping dict
        mapping = self._get_mapping_dict()
        sub_type_label = sub_type == "expense" and _("Expense") or _("Revenue")
        lsign = sub_type == "expense" and -1 or 1
        for sub in work.keys():
            vals = self._prepare_subscription_cutoff_line(
                work[sub], mapping, sub_type_label, lsign
            )
            if vals:
                line_obj.create(vals)
        return res

    def _prepare_subscription_cutoff_line(self, data, mapping, sub_type_label, lsign):
        # Compute provision for a subscription
        # -> analyse each time interval
        # Write the details of the computation in the notes
        # (or in the chatter if the amount to provision is 0)
        sub = data["sub"]
        ccur = self.company_currency_id
        notes = [
            _(
                "CONFIG: %s periodicity, start date %s, "
                "min. expense amount %s, default provision amount %s"
            )
            % (
                sub._fields["periodicity"].convert_to_export(sub.periodicity, sub),
                format_date(self.env, sub.start_date),
                format_amount(self.env, sub.min_amount, ccur),
                format_amount(self.env, sub.provision_amount, ccur),
            ),
            _("PERIODS:"),
        ]
        cutoff_amount = 0
        for interval in data["intervals"]:
            prorata_label = (
                interval["prorata"]
                and " "
                + _("PRORATED min. amount %s, default provisionning amount %s")
                % (
                    format_amount(self.env, interval["min_amount"], ccur),
                    format_amount(self.env, interval["provision_amount"], ccur),
                )
                or ""
            )
            if ccur.compare_amounts(interval["amount"], interval["min_amount"]) < 0:
                period_cutoff_amount = ccur.round(
                    interval["provision_amount"] - interval["amount"]
                )
                notes.append(
                    _("%s → %s%s: %s %s under min. amount ⇒provisionning %s")
                    % (
                        format_date(self.env, interval["start"]),
                        format_date(self.env, interval["end"]),
                        prorata_label,
                        sub_type_label,
                        format_amount(self.env, interval["amount"], ccur),
                        format_amount(self.env, period_cutoff_amount, ccur),
                    )
                )
                cutoff_amount += period_cutoff_amount * lsign
            else:
                notes.append(
                    _("%s → %s%s: %s %s over min. amount ⇒ no provisionning")
                    % (
                        format_date(self.env, interval["start"]),
                        format_date(self.env, interval["end"]),
                        prorata_label,
                        sub_type_label,
                        format_amount(self.env, interval["amount"], ccur),
                    )
                )
        if ccur.is_zero(cutoff_amount):
            msg = _(
                "<p>No provision for subscription <a href=# "
                "data-oe-model=account.cutoff.accrual.subscription "
                "data-oe-id=%d>%s</a>:</p>"
            ) % (sub.id, sub.name)
            if notes:
                msg += "<ul>"
                for note in notes:
                    msg += "<li>%s</li>" % note
                msg += "</ul>"
            self.message_post(body=msg)
            return False
        else:
            if sub.partner_type == "one":
                partner_id = sub.partner_id.id
            else:
                partner_id = False
            if sub.account_id.id in mapping:
                cutoff_account_id = mapping[sub.account_id.id]
            else:
                cutoff_account_id = sub.account_id.id
            vals = {
                "subscription_id": sub.id,
                "parent_id": self.id,
                "manual": False,
                "partner_id": partner_id,
                "account_id": sub.account_id.id,
                "analytic_account_id": sub.analytic_account_id.id or False,
                "name": sub.name,
                "currency_id": sub.company_currency_id.id,
                "amount": 0,
                "cutoff_amount": cutoff_amount,
                "cutoff_account_id": cutoff_account_id,
                "notes": "\n".join(notes),
            }
            if sub.tax_ids and self.company_id.accrual_taxes:
                vals["tax_ids"] = [(6, 0, sub.tax_ids.ids)]
            return vals

    class AccountCutoffLine(models.Model):
        _inherit = "account.cutoff.line"

        subscription_id = fields.Many2one(
            "account.cutoff.accrual.subscription", ondelete="restrict"
        )
