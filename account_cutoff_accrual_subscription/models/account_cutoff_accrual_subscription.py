# Copyright 2019-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

logger = logging.getLogger(__name__)


class AccountCutoffAccrualSubscription(models.Model):
    _name = "account.cutoff.accrual.subscription"
    _inherit = "analytic.mixin"
    _description = "Subscriptions to compute accrual cutoffs"
    _order = "subscription_type, name"
    _check_company_auto = True

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        ondelete="cascade",
        required=True,
        default=lambda self: self.env.company,
    )
    company_currency_id = fields.Many2one(
        string="Company Currency", related="company_id.currency_id", store=True
    )
    name = fields.Char(required=True)
    subscription_type = fields.Selection(
        [
            ("revenue", "Revenue"),
            ("expense", "Expense"),
        ],
        default="expense",
        required=True,
        string="Type",
    )
    partner_type = fields.Selection(
        [
            ("any", "Any Partner"),
            ("one", "Specific Partner"),
            ("none", "No Partner"),
        ],
        default="one",
        required=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        compute="_compute_partner_id",
        readonly=False,
        store=True,
        precompute=True,
        string="Partner",
        domain=[("parent_id", "=", False)],
        ondelete="restrict",
    )
    active = fields.Boolean(default=True)
    periodicity = fields.Selection(
        [
            ("month", "Monthly"),
            ("quarter", "Quarterly"),
            ("semester", "Semesterly"),
            ("year", "Yearly"),
        ],
        required=True,
    )
    start_date = fields.Date(required=True)
    min_amount = fields.Monetary(
        string="Minimum Amount",
        required=True,
        currency_field="company_currency_id",
        help="Minimum amount without taxes over the period",
    )
    provision_amount = fields.Monetary(
        compute="_compute_provision_amount",
        readonly=False,
        store=True,
        precompute=True,
        string="Default Provision Amount",
        currency_field="company_currency_id",
    )
    account_id = fields.Many2one(
        "account.account",
        string="Account",
        required=True,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
    )
    type_tax_use = fields.Char(compute="_compute_type_tax_use")
    tax_ids = fields.Many2many(
        "account.tax",
        compute="_compute_tax_ids",
        readonly=False,
        store=True,
        precompute=True,
        string="Taxes",
        domain="[('price_include', '=', False), ('company_id', '=', company_id), "
        "('type_tax_use', '=', type_tax_use)]",
        check_company=True,
    )

    @api.depends("subscription_type")
    def _compute_type_tax_use(self):
        mapping = {
            "revenue": "sale",
            "expense": "purchase",
        }
        for sub in self:
            sub.type_tax_use = mapping.get(sub.subscription_type)

    @api.constrains("start_date")
    def check_start_date(self):
        for sub in self:
            if sub.start_date.day != 1:
                raise ValidationError(
                    _(
                        "On subscription %s, the start date is not the first "
                        "day of a month."
                    )
                    % sub.display_name
                )

    _sql_constraints = [
        (
            "min_amount_positive",
            "CHECK(min_amount >= 0)",
            "The minimum amount must be positive.",
        ),
        (
            "provision_amount_positive",
            "CHECK(provision_amount >= 0)",
            "The default provision amount must be positive.",
        ),
    ]

    @api.depends("min_amount")
    def _compute_provision_amount(self):
        for sub in self:
            if sub.company_currency_id.compare_amounts(
                sub.min_amount, 0
            ) > 0 and sub.company_currency_id.is_zero(sub.provision_amount):
                sub.provision_amount = sub.min_amount

    @api.depends("account_id")
    def _compute_tax_ids(self):
        for sub in self:
            if sub.account_id:
                sub.tax_ids = sub.account_id.tax_ids

    @api.depends("partner_type")
    def _compute_partner_id(self):
        for sub in self:
            if sub.partner_type != "one":
                sub.partner_id = False

    def _process_subscription(
        self, work, fy_start_date, cutoff_date, common_domain, sign
    ):
        self.ensure_one()
        logger.debug("Processing subscription %s", self.display_name)
        aml_obj = self.env["account.move.line"]
        periodicity2months = {
            "month": 1,
            "quarter": 3,
            "semester": 6,
            "year": 12,
        }
        company = self.company_id
        ccur = company.currency_id
        months = periodicity2months[self.periodicity]
        work[self] = {"intervals": [], "sub": self}
        domain_base = common_domain + [
            ("company_id", "=", company.id),
            ("account_id", "=", self.account_id.id),
        ]
        if self.partner_type == "one":
            if self.partner_id:
                domain_base.append(("partner_id", "=", self.partner_id.id))
            else:
                raise UserError(
                    _("Missing partner on subscription '%s'.") % self.display_name
                )
        elif self.partner_type == "none":
            domain_base.append(("partner_id", "=", False))
        domain_base_w_start_end = domain_base + [
            ("start_date", "!=", False),
            ("end_date", "!=", False),
        ]

        start_date = fy_start_date  # initialize start_date
        while start_date < cutoff_date:
            end_date = start_date + relativedelta(day=31, months=(months - 1))
            logger.debug("Compute interval from %s to %s", start_date, end_date)
            if self.start_date > end_date:
                logger.debug(
                    "Skip interval because subscription start_date %s > end_date",
                    self.start_date,
                )
                start_date = end_date + relativedelta(days=1)
                continue
            # the next start_date is set at the very end of this method
            min_amount = self.min_amount
            provision_amount = self.provision_amount
            prorata = False
            if end_date > cutoff_date or self.start_date > start_date:
                prorata = True
                initial_interval_days = (end_date - start_date).days + 1
                if end_date > cutoff_date:
                    end_date = cutoff_date
                if self.start_date > start_date:
                    start_date = self.start_date
                final_interval_days = (end_date - start_date).days + 1
                ratio = final_interval_days / initial_interval_days
                min_amount = ccur.round(min_amount * ratio)
                provision_amount = ccur.round(provision_amount * ratio)
                logger.debug(
                    "Interval has been prorated: %s to %s "
                    "initial_interval_days=%d final_interval_days=%s",
                    start_date,
                    end_date,
                    initial_interval_days,
                    final_interval_days,
                )
                logger.debug(
                    "min_amount prorated from %s to %s", self.min_amount, min_amount
                )
                logger.debug(
                    "provision_amount prorated from %s to %s",
                    self.provision_amount,
                    provision_amount,
                )
            # compute amount
            amount = 0
            # 1. No start/end dates
            no_start_end_res = aml_obj._read_group(
                domain_base
                + [
                    ("date", "<=", end_date),
                    ("date", ">=", start_date),
                    ("start_date", "=", False),
                    ("end_date", "=", False),
                ],
                aggregates=["balance:sum"],
            )
            amount_no_start_end = no_start_end_res and no_start_end_res[0][0] or 0
            amount += amount_no_start_end * sign
            # 2. Start/end dates, INSIDE interval
            inside_res = aml_obj._read_group(
                domain_base_w_start_end
                + [
                    ("start_date", ">=", start_date),
                    ("end_date", "<=", end_date),
                ],
                aggregates=["balance:sum"],
            )
            amount_inside = inside_res and inside_res[0][0] or 0
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

            work[self]["intervals"].append(
                {
                    "start": start_date,
                    "end": end_date,
                    "amount": ccur.round(amount),
                    "prorata": prorata,
                    "min_amount": min_amount,
                    "provision_amount": provision_amount,
                }
            )
            # prepare next interval
            start_date = end_date + relativedelta(days=1)
