# Copyright 2016-2021 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountCutoff(models.Model):
    _inherit = "account.cutoff"

    @api.model
    def _get_default_source_journals(self):
        res = []
        cutoff_type = self.env.context.get("default_cutoff_type")
        mapping = {
            "accrued_revenue": "sale",
            "accrued_expense": "purchase",
            "prepaid_revenue": "sale",
            "prepaid_expense": "purchase",
        }
        if cutoff_type in mapping:
            src_journals = self.env["account.journal"].search(
                [
                    ("type", "=", mapping[cutoff_type]),
                    ("company_id", "=", self.env.company.id),
                ]
            )
            if src_journals:
                res = src_journals.ids
        return res

    source_journal_ids = fields.Many2many(
        "account.journal",
        column1="cutoff_id",
        column2="journal_id",
        string="Source Journals",
        default=lambda self: self._get_default_source_journals(),
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    forecast = fields.Boolean(
        readonly=True,
        tracking=True,
        help="The Forecast mode allows the user to compute "
        "the prepaid revenue/expense between 2 dates in the future.",
    )
    start_date = fields.Date()
    end_date = fields.Date()

    @api.constrains("start_date", "end_date", "forecast")
    def _check_start_end_dates(self):
        for rec in self:
            if (
                rec.forecast
                and rec.start_date
                and rec.end_date
                and rec.start_date > rec.end_date
            ):
                raise ValidationError(_("The start date is after the end date!"))

    def forecast_enable(self):
        self.ensure_one()
        assert self.state == "draft"
        if self.move_id:
            raise UserError(
                _(
                    "This cutoff is linked to a journal entry. "
                    "You must delete it before entering forecast mode."
                )
            )
        self.line_ids.unlink()
        self.write({"forecast": True})

    def forecast_disable(self):
        self.ensure_one()
        assert self.state == "draft"
        self.line_ids.unlink()
        self.write({"forecast": False})

    def _prepare_date_cutoff_line(self, aml, mapping):
        self.ensure_one()
        total_days = (aml.end_date - aml.start_date).days + 1
        assert total_days > 0, "Should never happen. Total days should always be > 0"
        # we use account mapping here
        if aml.account_id.id in mapping:
            cutoff_account_id = mapping[aml.account_id.id]
        else:
            cutoff_account_id = aml.account_id.id
        vals = {
            "parent_id": self.id,
            "origin_move_line_id": aml.id,
            "partner_id": aml.partner_id.id or False,
            "name": aml.name,
            "start_date": aml.start_date,
            "end_date": aml.end_date,
            "account_id": aml.account_id.id,
            "cutoff_account_id": cutoff_account_id,
            "analytic_account_id": aml.analytic_account_id.id or False,
            "total_days": total_days,
            "amount": -aml.balance,
            "currency_id": self.company_currency_id.id,
            "tax_line_ids": [],
        }
        if self.cutoff_type in ["prepaid_expense", "prepaid_revenue"]:
            self._prepare_date_prepaid_cutoff_line(aml, vals)
        elif self.cutoff_type in ["accrued_expense", "accrued_revenue"]:
            self._prepare_date_accrual_cutoff_line(aml, vals)
        return vals

    def _prepare_date_accrual_cutoff_line(self, aml, vals):
        self.ensure_one()
        start_date_dt = aml.start_date
        end_date_dt = aml.end_date
        # Here, we compute the amount of the cutoff
        # That's the important part !
        cutoff_date_dt = self.cutoff_date
        if end_date_dt <= cutoff_date_dt:
            cutoff_days = vals["total_days"]
        else:
            cutoff_days = (cutoff_date_dt - start_date_dt).days + 1
        cutoff_amount = -aml.balance * cutoff_days / vals["total_days"]
        cutoff_amount = self.company_currency_id.round(cutoff_amount)

        vals.update(
            {
                "cutoff_days": cutoff_days,
                "cutoff_amount": cutoff_amount,
            }
        )

        if aml.tax_ids and self.company_id.accrual_taxes:
            tax_compute_all_res = aml.tax_ids.compute_all(
                cutoff_amount,
                product=aml.product_id,
                partner=aml.partner_id,
                handle_price_include=False,
            )
            vals["tax_line_ids"] = self._prepare_tax_lines(
                tax_compute_all_res, self.company_currency_id
            )

    def _prepare_date_prepaid_cutoff_line(self, aml, vals):
        self.ensure_one()
        start_date_dt = aml.start_date
        end_date_dt = aml.end_date
        # Here, we compute the amount of the cutoff
        # That's the important part !
        if self.forecast:
            out_days = 0
            forecast_start_date_dt = self.start_date
            forecast_end_date_dt = self.end_date
            if end_date_dt > forecast_end_date_dt:
                out_days += (end_date_dt - forecast_end_date_dt).days
            if start_date_dt < forecast_start_date_dt:
                out_days += (forecast_start_date_dt - start_date_dt).days
            cutoff_days = vals["total_days"] - out_days
        else:
            cutoff_date_dt = self.cutoff_date
            if start_date_dt > cutoff_date_dt:
                cutoff_days = vals["total_days"]
            else:
                cutoff_days = (end_date_dt - cutoff_date_dt).days
        cutoff_amount = aml.balance * cutoff_days / vals["total_days"]
        cutoff_amount = self.company_currency_id.round(cutoff_amount)

        vals.update(
            {
                "cutoff_days": cutoff_days,
                "cutoff_amount": cutoff_amount,
            }
        )

    def get_lines(self):
        res = super().get_lines()
        aml_obj = self.env["account.move.line"]
        line_obj = self.env["account.cutoff.line"]
        if not self.source_journal_ids:
            raise UserError(_("You should set at least one Source Journal."))
        mapping = self._get_mapping_dict()
        domain = [
            ("journal_id", "in", self.source_journal_ids.ids),
            ("display_type", "=", False),
            ("company_id", "=", self.company_id.id),
            ("balance", "!=", 0),
        ]

        if self.cutoff_type in ["prepaid_expense", "prepaid_revenue"]:
            if self.forecast:
                domain += [
                    ("start_date", "!=", False),
                    ("start_date", "<=", self.end_date),
                    ("end_date", ">=", self.start_date),
                ]
            else:
                domain += [
                    ("start_date", "!=", False),
                    ("end_date", ">", self.cutoff_date),
                    ("date", "<=", self.cutoff_date),
                ]
        elif self.cutoff_type in ["accrued_expense", "accrued_revenue"]:
            domain += [
                ("start_date", "!=", False),
                ("start_date", "<=", self.cutoff_date),
                ("date", ">", self.cutoff_date),
            ]
        amls = aml_obj.search(domain)
        for aml in amls:
            line_obj.create(self._prepare_date_cutoff_line(aml, mapping))
        return res


class AccountCutoffLine(models.Model):
    _inherit = "account.cutoff.line"

    start_date = fields.Date(readonly=True)
    end_date = fields.Date(readonly=True)
    total_days = fields.Integer(readonly=True)
    cutoff_days = fields.Integer(
        readonly=True,
        help="In regular mode, this is the number of days after the "
        "cut-off date. In forecast mode, this is the number of days "
        "between the start date and the end date.",
    )  # Old name: prepaid_days
