# Copyright 2016-2022 Akretion France
# Copyright 2026 Tecnativa - Adasat Torres
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountCutoff(models.Model):
    _inherit = "account.cutoff"

    calculation_method = fields.Selection(
        selection=[
            ("pending", "Pending Amount"),
            ("difference", "Difference Since Last Cut-off"),
        ],
        required=True,
        default="pending",
        tracking=True,
    )
    source_journal_ids = fields.Many2many(
        "account.journal",
        column1="cutoff_id",
        column2="journal_id",
        string="Source Journals",
        compute="_compute_source_journal_ids",
        store=True,
        readonly=False,
        precompute=True,
        check_company=True,
        domain="[('company_id', '=', company_id)]",
    )
    previous_cutoff_id = fields.Many2one(
        "account.cutoff", readonly=True, copy=False, check_company=True
    )

    def _is_difference_cutoff(self):
        self.ensure_one()
        return self.calculation_method == "difference" and self.state != "forecast"

    @api.constrains("calculation_method", "auto_reverse", "cutoff_type", "state")
    def _check_difference_method(self):
        for rec in self:
            if rec.calculation_method != "difference":
                continue
            if rec.auto_reverse or rec.state == "forecast":
                raise ValidationError(
                    self.env._(
                        "Difference calculation requires no "
                        "automatic reversal or forecast mode."
                    )
                )

    @api.onchange("calculation_method")
    def _onchange_calculation_method(self):
        if self.calculation_method == "difference":
            self.auto_reverse = False

    def _get_previous_difference_cutoff(self):
        self.ensure_one()
        domain = [
            ("company_id", "=", self.company_id.id),
            ("cutoff_type", "=", self.cutoff_type),
            ("id", "!=", self.id),
            ("move_id", "!=", False),
        ]
        # Inserting a historical cut-off would invalidate later differences.
        if self.search_count(domain + [("cutoff_date", ">", self.cutoff_date)]):
            raise UserError(self.env._("A later cut-off already exists."))
        previous = self.search(
            domain + [("cutoff_date", "<", self.cutoff_date)],
            order="cutoff_date desc",
            limit=1,
        )
        if not previous:
            return previous
        if previous.move_id.state != "posted":
            raise UserError(
                self.env._(
                    "Post the journal entry of the previous cut-off "
                    "%(name)s before generating this one.",
                    name=previous.display_name,
                )
            )
        if previous.calculation_method != "difference":
            reversal = previous.move_reversal_id
            # A draft or future-dated reversal has not cleared the balance
            # at this cut-off date, so starting from zero would duplicate it.
            if reversal.state == "posted" and reversal.date <= self.cutoff_date:
                # A fully reversed regular cut-off carries no pending balance.
                return self.browse()
            raise UserError(
                self.env._(
                    "The previous regular cut-off must have a posted reversal "
                    "dated on or before this cut-off to start from zero."
                )
            )
        if previous.move_reversal_id:
            raise UserError(
                self.env._("The previous difference cut-off must not be reversed.")
            )
        return previous

    def create_move(self):
        if self._is_difference_cutoff():
            previous = self._get_previous_difference_cutoff()
            # Another cut-off may have been posted since these lines were
            # generated; their stored differences would then be outdated.
            if previous != self.previous_cutoff_id:
                raise UserError(
                    self.env._(
                        "The previous cut-off changed. Generate the lines again."
                    )
                )
            if self.auto_reverse:
                raise UserError(
                    self.env._("Disable automatic reversal for difference calculation.")
                )
        return super().create_move()

    def back2draft(self):
        # Dependent lines contain snapshots of this cut-off's balance.
        # Reset the chain from newest to oldest to preserve those references.
        if self.search_count(
            [("previous_cutoff_id", "in", self.ids), ("state", "=", "done")]
        ):
            raise UserError(self.env._("Reset dependent cut-offs to draft first."))
        res = super().back2draft()
        self.previous_cutoff_id = False
        return res

    state = fields.Selection(selection_add=[("forecast", "Forecast")])
    start_date = fields.Date(help="This field is only for the forecast mode")
    end_date = fields.Date(help="This field is only for the forecast mode")
    include_tax_lines = fields.Boolean(
        help="If enabled, tax move lines (display_type = 'tax') will also "
        "be included in the cutoff computation alongside product lines. "
        "Tax lines must have start and end dates set to be included.",
    )

    @api.depends("company_id", "cutoff_type")
    def _compute_source_journal_ids(self):
        mapping = {
            "accrued_revenue": "sale",
            "accrued_expense": "purchase",
            "prepaid_revenue": "sale",
            "prepaid_expense": "purchase",
        }
        for rec in self:
            source_journal_ids = []
            if rec.cutoff_type in mapping:
                src_journals = self.env["account.journal"].search(
                    [
                        ("type", "=", mapping[rec.cutoff_type]),
                        ("company_id", "=", rec.company_id.id),
                    ]
                )
                source_journal_ids = src_journals.ids
            rec.source_journal_ids = [Command.set(source_journal_ids)]

    @api.constrains("start_date", "end_date", "state")
    def _check_start_end_dates(self):
        for rec in self:
            if (
                rec.state == "forecast"
                and rec.start_date
                and rec.end_date
                and rec.start_date > rec.end_date
            ):
                raise ValidationError(
                    self.env._("The start date is after the end date!")
                )

    def forecast_enable(self):
        self.ensure_one()
        assert self.state == "draft"
        if self.move_id:
            raise UserError(
                self.env._(
                    "This cutoff is linked to a journal entry. "
                    "You must delete it before entering forecast mode."
                )
            )
        self.line_ids.unlink()
        # set cutoff_date to False to avoid issue with unicity sql constraint
        # The difference method doesn't exist in forecast mode.
        self.write(
            {
                "state": "forecast",
                "cutoff_date": False,
                "calculation_method": "pending",
            }
        )

    def forecast_disable(self):
        self.ensure_one()
        assert self.state == "forecast"
        self.line_ids.unlink()
        self.write({"state": "draft"})

    def _prepare_date_cutoff_line(self, aml, mapping, previous_lines=None):
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
            "analytic_distribution": aml.analytic_distribution,
            "total_days": total_days,
            "amount": -aml.balance,
            "currency_id": self.company_currency_id.id,
            "tax_line_ids": [],
        }
        if self.cutoff_type in ["prepaid_expense", "prepaid_revenue"]:
            self._prepare_date_prepaid_cutoff_line(aml, vals)
        elif self.cutoff_type in ["accrued_expense", "accrued_revenue"]:
            self._prepare_date_accrual_cutoff_line(aml, vals)
        if self._is_difference_cutoff():
            self._apply_previous_cutoff_amount(aml, vals, previous_lines)
        return vals

    def _prepare_released_cutoff_line(self, previous_line):
        self.ensure_one()
        # Use the booked snapshot: the source may no longer have service dates
        # or may now use different accounts or analytics.
        vals = {
            "parent_id": self.id,
            "origin_move_line_id": previous_line.origin_move_line_id.id,
            "partner_id": previous_line.partner_id.id,
            "name": previous_line.name,
            "start_date": previous_line.start_date,
            "end_date": previous_line.end_date,
            "account_id": previous_line.account_id.id,
            "cutoff_account_id": previous_line.cutoff_account_id.id,
            "analytic_distribution": previous_line.analytic_distribution,
            "total_days": previous_line.total_days,
            "cutoff_days": 0,
            "amount": previous_line.amount,
            "currency_id": previous_line.currency_id.id,
            "cutoff_amount": 0,
            "pending_amount": 0,
            "tax_line_ids": [],
        }
        self._apply_previous_cutoff_amount(
            previous_line.origin_move_line_id, vals, previous_line
        )
        return vals

    def _prepare_date_accrual_cutoff_line(self, aml, vals):
        self.ensure_one()
        start_date_dt = aml.start_date
        end_date_dt = aml.end_date
        # Here, we compute the amount of the cutoff
        # That's the important part !
        cutoff_date_dt = self.cutoff_date
        if self._is_difference_cutoff() and aml.date <= cutoff_date_dt:
            # The invoice now recognizes the expense/revenue itself.
            # A zero target balance releases the previous accrual in full.
            cutoff_days = 0
        elif end_date_dt <= cutoff_date_dt:
            cutoff_days = vals["total_days"]
        else:
            cutoff_days = max(0, (cutoff_date_dt - start_date_dt).days + 1)
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
        if self.state == "forecast":
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
                cutoff_days = max(0, (end_date_dt - cutoff_date_dt).days)
        cutoff_amount = aml.balance * cutoff_days / vals["total_days"]
        cutoff_amount = self.company_currency_id.round(cutoff_amount)

        vals.update(
            {
                "cutoff_days": cutoff_days,
                "cutoff_amount": cutoff_amount,
                "pending_amount": cutoff_amount,
            }
        )

    def _apply_previous_cutoff_amount(self, aml, vals, previous_lines=None):
        # Match source journal items rather than accounts: several invoice
        # lines can share an account but have different service periods.
        if previous_lines is None:
            previous_lines = self.previous_cutoff_id.line_ids.filtered(
                lambda line: line.origin_move_line_id == aml
            )
        previous_amount = sum(previous_lines.mapped("pending_amount"))
        pending_amount = vals["cutoff_amount"]
        # Keep the cumulative target separately: the previous journal entry
        # contains only a variation and cannot serve as the next baseline.
        vals.update(
            pending_amount=pending_amount,
            previous_pending_amount=previous_amount,
            cutoff_amount=self.company_currency_id.round(
                pending_amount - previous_amount
            ),
        )
        # Calculate tax variations from rounded cumulative amounts as well.
        previous_taxes = {
            (tax.tax_id.id, tax.cutoff_account_id.id): tax
            for tax in previous_lines.tax_line_ids
        }
        commands = []
        for command in vals["tax_line_ids"]:
            tax_vals = dict(command[2])
            key = (tax_vals["tax_id"], tax_vals["cutoff_account_id"])
            previous_tax = previous_taxes.pop(key, False)
            for field in ("base", "amount", "cutoff_amount"):
                # Snapshot the cumulative value before replacing it by its delta.
                tax_vals["pending_" + field] = tax_vals[field]
                if previous_tax:
                    tax_vals[field] -= previous_tax["pending_" + field]
            commands.append(Command.create(tax_vals))
        # Taxes missing from the current calculation still need their previous
        # balance released, notably when the invoice date has been reached.
        for tax in previous_taxes.values():
            commands.append(
                Command.create(
                    {
                        "tax_id": tax.tax_id.id,
                        "cutoff_account_id": tax.cutoff_account_id.id,
                        "sequence": tax.sequence,
                        "analytic_distribution": tax.analytic_distribution,
                        "base": -tax.pending_base,
                        "amount": -tax.pending_amount,
                        "cutoff_amount": -tax.pending_cutoff_amount,
                    }
                )
            )
        vals["tax_line_ids"] = commands

    def get_lines(self):
        res = super().get_lines()
        self.previous_cutoff_id = (
            self._get_previous_difference_cutoff()
            if self._is_difference_cutoff()
            else False
        )
        aml_obj = self.env["account.move.line"]
        line_obj = self.env["account.cutoff.line"]
        if not self.source_journal_ids:
            raise UserError(self.env._("You should set at least one Source Journal."))
        mapping = self._get_mapping_dict()
        if self.include_tax_lines:
            display_types = ("product", "tax")
        else:
            display_types = ("product",)
        domain = [
            ("journal_id", "in", self.source_journal_ids.ids),
            ("display_type", "in", display_types),
            ("company_id", "=", self.company_id.id),
            ("balance", "!=", 0),
            ("start_date", "!=", False),
            ("end_date", "!=", False),
        ]
        if self.source_move_state == "posted":
            domain.append(("parent_state", "=", "posted"))
        else:
            domain.append(("parent_state", "in", ("draft", "posted")))

        source_domain = list(domain)
        if self.cutoff_type in ["prepaid_expense", "prepaid_revenue"]:
            if self.state == "forecast":
                if not self.start_date or not self.end_date:
                    raise UserError(
                        self.env._(
                            "Start date and end date are required for forecast mode."
                        )
                    )
                domain += [
                    ("start_date", "<=", self.end_date),
                    ("end_date", ">=", self.start_date),
                ]
            else:
                domain += [
                    ("end_date", ">", self.cutoff_date),
                    ("date", "<=", self.cutoff_date),
                ]
        elif self.cutoff_type in ["accrued_expense", "accrued_revenue"]:
            domain += [
                ("start_date", "<=", self.cutoff_date),
                ("date", ">", self.cutoff_date),
            ]
        amls = aml_obj.search(domain)
        previous_lines_by_aml = {}
        if self._is_difference_cutoff():
            # Group all previous lines once, including zero balances whose
            # tax snapshots may still be needed when computing differences.
            previous_lines_by_aml = self.previous_cutoff_id.line_ids.grouped(
                "origin_move_line_id"
            )
            # The normal domain excludes completed prepaids and invoiced
            # accruals. Keep their sources to release the previous balance,
            # unless it was already released (nothing left to release).
            previous_lines = self.previous_cutoff_id.line_ids.filtered("pending_amount")
            valid_sources = previous_lines.origin_move_line_id.filtered_domain(
                source_domain
            )
            amls |= valid_sources
            for previous_line in previous_lines.filtered(
                lambda line: line.origin_move_line_id not in valid_sources
            ):
                line_obj.create(self._prepare_released_cutoff_line(previous_line))
        for aml in amls:
            line_obj.create(
                self._prepare_date_cutoff_line(
                    aml, mapping, previous_lines_by_aml.get(aml, line_obj)
                )
            )
        return res
