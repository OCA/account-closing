# Copyright 2019-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, float_round
from odoo.tools.misc import formatLang


class AccountCutoff(models.Model):
    _inherit = "account.cutoff"

    def get_lines(self):
        res = super().get_lines()
        if self.cutoff_type not in ["accrued_expense", "accrued_revenue"]:
            return res
        aml_obj = self.env["account.move.line"]
        line_obj = self.env["account.cutoff.line"]
        sub_obj = self.env["account.cutoff.accrual.subscription"]
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
                    % self.cutoff_date
                )
            if not self.source_journal_ids:
                raise UserError(_("Missing source journals."))
            self.message_post(
                body=_("Computing provisions from %d subscriptions.") % len(subs)
            )
        periodicity2months = {
            "month": 1,
            "quarter": 3,
            "semester": 6,
            "year": 12,
        }
        company_currency = self.company_currency_id
        prec = company_currency.rounding
        work = {}
        # Generate time intervals and compute existing expenses/revenue
        for sub in subs:
            months = periodicity2months[sub.periodicity]
            work[sub] = {"intervals": [], "sub": sub}
            end_date = self.cutoff_date
            domain_base = [
                ("company_id", "=", sub.company_id.id),
                ("journal_id", "in", self.source_journal_ids.ids),
                ("account_id", "=", sub.account_id.id),
                ("analytic_account_id", "=", sub.analytic_account_id.id or False),
            ]
            if sub.partner_type == "one":
                if sub.partner_id:
                    domain_base.append(("partner_id", "=", sub.partner_id.id))
                else:
                    raise UserError(
                        _("Missing supplier on subscription '%s'.") % sub.display_name
                    )
            elif sub.partner_type == "none":
                domain_base.append(("partner_id", "=", False))
            domain_base_w_start_end = domain_base + [
                ("start_date", "!=", False),
                ("end_date", "!=", False),
            ]

            for _i in range(int(12 / months)):
                start_date = end_date + relativedelta(day=1, months=-(months - 1))
                if start_date < sub.start_date:
                    break
                # compute amount
                amount = 0
                # 1. No start/end dates
                no_start_end_res = aml_obj.read_group(
                    domain_base
                    + [
                        ("date", "<=", fields.Date.to_string(end_date)),
                        ("date", ">=", fields.Date.to_string(start_date)),
                        ("start_date", "=", False),
                        ("end_date", "=", False),
                    ],
                    ["balance"],
                    [],
                )
                amount_no_start_end = (
                    no_start_end_res and no_start_end_res[0]["balance"] or 0
                )
                amount += amount_no_start_end * sign
                # 2. Start/end dates, INSIDE interval
                inside_res = aml_obj.read_group(
                    domain_base_w_start_end
                    + [
                        ("start_date", ">=", start_date),
                        ("end_date", "<=", end_date),
                    ],
                    ["balance"],
                    [],
                )
                amount_inside = inside_res and inside_res[0]["balance"] or 0
                amount += amount_inside * sign
                # 3. Start/end dates, OVER interval
                mlines = aml_obj.search(
                    domain_base_w_start_end
                    + [
                        ("start_date", "<", start_date),
                        ("end_date", ">", end_date),
                    ]
                )
                for mline in mlines:
                    total_days = (mline.end_date - mline.start_date).days + 1
                    days_in_interval = (end_date - start_date).days + 1
                    amount_in_interval = mline.balance * days_in_interval / total_days
                    amount += amount_in_interval * sign
                # 4. Start/end dates, start_date before, end_date inside
                mlines = aml_obj.search(
                    domain_base_w_start_end
                    + [
                        ("start_date", "<", start_date),
                        ("end_date", ">=", start_date),
                        ("end_date", "<=", end_date),
                    ]
                )
                for mline in mlines:
                    total_days = (mline.end_date - mline.start_date).days + 1
                    days_in_interval = (mline.end_date - start_date).days + 1
                    amount_in_interval = mline.balance * days_in_interval / total_days
                    amount += amount_in_interval * sign
                # 5. Start/end dates, start_date inside, end_date after
                mlines = aml_obj.search(
                    domain_base_w_start_end
                    + [
                        ("start_date", ">=", start_date),
                        ("start_date", "<=", end_date),
                        ("end_date", ">", end_date),
                    ]
                )
                for mline in mlines:
                    total_days = (mline.end_date - mline.start_date).days + 1
                    days_in_interval = (end_date - mline.start_date).days + 1
                    amount_in_interval = mline.balance * days_in_interval / total_days
                    amount += amount_in_interval * sign

                work[sub]["intervals"].append(
                    {
                        "start": start_date,
                        "end": end_date,
                        "amount": float_round(amount, precision_rounding=prec),
                    }
                )
                # prepare next interval
                end_date = start_date + relativedelta(days=-1)
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
        company_currency = self.company_currency_id
        prec = company_currency.rounding
        notes = []
        cutoff_amount = 0
        for interval in data["intervals"]:
            if (
                float_compare(
                    interval["amount"], sub.min_amount, precision_rounding=prec
                )
                < 0
            ):
                period_cutoff_amount = self.company_currency_id.round(
                    sub.provision_amount - interval["amount"]
                )
                notes.append(
                    _(
                        "Period from %s to %s: %s %s under the minimum "
                        "amount %s. Default provisionning amount is %s "
                        "=> provisionning %s."
                    )
                    % (
                        fields.Date.to_string(interval["start"]),
                        fields.Date.to_string(interval["end"]),
                        sub_type_label,
                        formatLang(
                            self.env,
                            interval["amount"],
                            currency_obj=self.company_currency_id,
                        ),
                        formatLang(
                            self.env,
                            sub.min_amount,
                            currency_obj=self.company_currency_id,
                        ),
                        formatLang(
                            self.env,
                            sub.provision_amount,
                            currency_obj=self.company_currency_id,
                        ),
                        formatLang(
                            self.env,
                            period_cutoff_amount,
                            currency_obj=self.company_currency_id,
                        ),
                    )
                )
                cutoff_amount += period_cutoff_amount * lsign
            else:
                notes.append(
                    _(
                        "Period from %s to %s: %s %s over the minimum "
                        "amount %s => no provisionning."
                    )
                    % (
                        fields.Date.to_string(interval["start"]),
                        fields.Date.to_string(interval["end"]),
                        sub_type_label,
                        formatLang(
                            self.env,
                            interval["amount"],
                            currency_obj=self.company_currency_id,
                        ),
                        formatLang(
                            self.env,
                            sub.min_amount,
                            currency_obj=self.company_currency_id,
                        ),
                    )
                )
        if float_is_zero(cutoff_amount, precision_rounding=prec):
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
                "parent_id": self.id,
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
                tax_compute_all_res = sub.tax_ids.compute_all(
                    cutoff_amount, partner=sub.partner_id, handle_price_include=False
                )
                vals["tax_line_ids"] = self._prepare_tax_lines(
                    tax_compute_all_res, company_currency
                )
            return vals
