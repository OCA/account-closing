# Copyright 2023 Foodles (http://www.foodles.co).
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models

logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = [
        "account.move.line",
        "cutoff.period.mixin",
    ]

    @api.model
    def _get_default_cutoff_method(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "account_move_cutoff.default_cutoff_method", "monthly_prorata_temporis"
            )
        )

    is_deferrable_line = fields.Boolean(
        string="Is deferrable line",
        compute="_compute_is_deferrable_line",
        help=("Field used to detect lines to cut-off"),
    )
    cutoff_method = fields.Selection(
        [
            ("equal", "Equal"),
            ("monthly_prorata_temporis", "Prorata temporis (by month %)"),
        ],
        string="Cut-off method",
        required=True,
        default=lambda self: self._get_default_cutoff_method(),
        help=(
            "Determine how to split amounts over periods:\n"
            " * Equal: same amount is splitted over periods of the service"
            "   (using start and end date on the invoice line).\n"
            " * Prorata temporis by month %: amount is splitted over"
            "   the rate of service days in the month.\n"
        ),
    )
    deferred_accrual_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Revenue/Expense accrual account",
        related="account_id.deferred_accrual_account_id",
        help=(
            "Use related field to abstract the way to get deferred accrual account. "
            "This will give the possibility to overwrite the way to configure it. "
            "For instance to use the same account without any configuration while "
            "creating new account."
        ),
    )

    cutoff_source_id = fields.Many2one(
        comodel_name="account.move.line",
        string="Cut-off source item",
        readonly=True,
        help="Source journal item that generate the current deferred revenue/expense item",
    )
    cutoff_source_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Cut-off source entry",
        related="cutoff_source_id.move_id",
        readonly=True,
        store=True,
    )
    cutoff_ids = fields.One2many(
        comodel_name="account.move.line",
        inverse_name="cutoff_source_id",
        string="Cut-off items",
        readonly=True,
        help=(
            "Field use to make easy to user to follow items generated "
            "from this specific entry to deferred revenues or expenses."
        ),
    )

    @api.depends(
        "move_id.date",
        "account_id",
        "deferred_accrual_account_id",
        "start_date",
        "end_date",
    )
    def _compute_is_deferrable_line(self):
        for move_line in self:
            if (
                move_line.start_date
                and move_line.end_date
                and move_line.move_id.date
                and move_line.deferred_accrual_account_id
                and not move_line.cutoff_ids
                and move_line.has_deferred_dates()
            ):
                move_line.is_deferrable_line = True
            else:
                move_line.is_deferrable_line = False

    def has_deferred_dates(self):
        """Compute the account move line should be split:
        has service in future periods
        """
        self.ensure_one()
        if self._period_from_date(self.end_date) > self._period_from_date(
            self.move_id.date
        ):
            return True
        return False

    @api.model
    def _get_first_day_from_period(self, period):
        return period

    @api.model
    def _get_last_day_from_period(self, period):
        return self._last_day_of_month(period)

    @api.model
    def _line_amounts_on_proper_periods(self, line_amounts, periods):
        extra_amount_first_period = 0
        extra_amount_last_period = 0
        amounts = defaultdict(lambda: 0)
        date_first_period = self._get_first_day_from_period(periods[0])
        date_end_period = self._get_last_day_from_period(periods[-1])
        for period, line_period_amount in line_amounts.items():
            if self._get_last_day_from_period(period) < date_first_period:
                extra_amount_first_period += line_period_amount
                continue
            if self._get_first_day_from_period(period) > date_end_period:
                extra_amount_last_period += line_period_amount
                continue
            amounts[period] = line_period_amount
        amounts[periods[0]] += extra_amount_first_period
        amounts[periods[-1]] += extra_amount_last_period
        return amounts

    def _round_amounts(self, line_periods):
        """This method is used to round values and avoid
        rounding side effects
        """
        amounts = {}
        sum_from_next_periods = 0
        first_period = None
        for index, item in enumerate(line_periods.items()):
            period, amount = item
            amounts[period] = self.currency_id.round(amount)
            if index > 0:
                sum_from_next_periods += amounts[period]
            else:
                first_period = period
        # avoid rounding difference
        if first_period:
            amounts[first_period] = self.currency_id.round(
                abs(self.balance) - sum_from_next_periods
            )
        return amounts

    def _get_amounts_per_periods(self, periods):
        """dispatch to the proper method"""
        self.ensure_one()
        line_amounts = {}
        if self.cutoff_method == "equal":
            line_amounts = self._get_amounts_per_periods_equal()
        else:  # monthly_prorata_temporis
            line_amounts = self._get_amounts_per_periods_monthly_prorata_temporis()
        line_amounts = self._line_amounts_on_proper_periods(line_amounts, periods)
        line_amounts = self._round_amounts(line_amounts)
        return line_amounts

    def _get_amounts_per_periods_equal(self):
        self.ensure_one()
        amounts = dict()
        line_periods = self._generate_monthly_periods(self.start_date, self.end_date)
        for period in line_periods:
            amounts[period] = abs(self.balance) / len(line_periods)
        return amounts

    def _get_amounts_per_periods_monthly_prorata_temporis(self):
        self.ensure_one()
        amounts = dict()
        line_periods = self._generate_monthly_periods(self.start_date, self.end_date)
        line_periods_factors = dict.fromkeys(line_periods, 1)
        last_day_first_period = self._last_day_of_month(line_periods[0])
        # use of +1 because service days includes start and end dates [start_date, end_date]
        line_periods_factors[line_periods[0]] = (
            (last_day_first_period - self.start_date).days + 1
        ) / last_day_first_period.day
        line_periods_factors[line_periods[-1]] = (
            self.end_date.day / self._last_day_of_month(line_periods[-1]).day
        )

        sum_factor = sum([factor for _period, factor in line_periods_factors.items()])
        for period, factor in line_periods_factors.items():
            amounts[period] = abs(self.balance) * factor / sum_factor

        return amounts

    def _get_deferred_amounts_by_period(self, periods):
        amounts_per_line_and_periods = []
        for line in self:
            amounts_per_line_and_periods.append(
                (line, line._get_amounts_per_periods(periods))
            )
        return amounts_per_line_and_periods

    def _get_period_start_end_dates(self, period):
        last_period_day = self._last_day_of_month(period)
        if self.start_date > last_period_day or self.end_date < period:
            start_date = None
            end_date = None
        else:
            start_date = max(self.start_date, period)
            end_date = min(self.end_date, self._last_day_of_month(period))
        return start_date, end_date

    def _get_deferred_expense_revenue_account_move_line_labels(self, is_cutoff=None):
        if is_cutoff:
            return _("Deferred incomes of %s (%s): %s") % (
                self.move_id.name,
                self.date.strftime("%m %Y"),
                self.name,
            )
        else:
            return _("Adjust deferred incomes of %s (%s): %s") % (
                self.move_id.name,
                self.date.strftime("%m %Y"),
                self.name,
            )

    def _prepare_entry_lines(self, new_move, period, amount, is_cutoff=True):
        self.ensure_one()
        if amount == 0:
            return self.env["account.move.line"].browse()
        reported_credit = reported_debit = 0
        if self.currency_id.compare_amounts(self.credit, 0) > 0:
            reported_credit = amount
            reported_debit = 0
        else:
            reported_debit = amount
            reported_credit = 0

        if is_cutoff:
            start_date = max(period + relativedelta(months=1, day=1), self.start_date)
            end_date = self.end_date
        else:
            start_date, end_date = self._get_period_start_end_dates(period)
        return self.env["account.move.line"].create(
            [
                {
                    "move_id": new_move.id,
                    "name": self._get_deferred_expense_revenue_account_move_line_labels(
                        is_cutoff=is_cutoff
                    ),
                    "start_date": start_date,
                    "end_date": end_date,
                    "debit": reported_credit if is_cutoff else reported_debit,
                    "credit": reported_debit if is_cutoff else reported_credit,
                    "currency_id": self.currency_id.id,
                    "account_id": self.account_id.id,
                    "partner_id": self.partner_id.id,
                    "analytic_account_id": self.analytic_account_id.id,
                    "cutoff_source_id": self.id,
                },
                {
                    "move_id": new_move.id,
                    "name": _("Adjusting Entry: %s (%s): %s")
                    % (
                        self.move_id.name,
                        self.date.strftime("%m %Y"),
                        self.name,
                    ),
                    "start_date": start_date,
                    "end_date": end_date,
                    "debit": reported_debit if is_cutoff else reported_credit,
                    "credit": reported_credit if is_cutoff else reported_debit,
                    "currency_id": self.currency_id.id,
                    "account_id": self.deferred_accrual_account_id.id,
                    "partner_id": self.partner_id.id,
                    "analytic_account_id": False,
                    "cutoff_source_id": self.id,
                },
            ]
        )

    def _create_cutoff_entry_lines(self, new_move, period, amount):
        """Return record set with new journal items (account.move.line)
        to link to the cuttoff entry for the current invoice line, with the
        amount defined here.

        We are not deferring VAT !
        """
        return self._prepare_entry_lines(new_move, period, amount)

    def _create_deferred_entry_lines(self, new_move, period, amount):
        """Return record set with new journal items (account.move.line)
        to link to the deferred entry for the current invoice line, with the
        amount defined here.

        We are not deferring VAT !
        """
        return self._prepare_entry_lines(new_move, period, amount, is_cutoff=False)
