# Copyright 2019-2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountCutoffAccrualSubscription(models.Model):
    _name = "account.cutoff.accrual.subscription"
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
            ("none", "No Partner"),
            ("one", "Specific Partner"),
            ("any", "Any Partner"),
        ],
        default="one",
        string="Partner Type",
        required=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Supplier",
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
        string="Periodicity",
        required=True,
    )
    start_date = fields.Date(required=True)
    min_amount = fields.Monetary(
        string="Minimum Expense Amount",
        required=True,
        currency_field="company_currency_id",
        help="Minimum expense amount without taxes over the period",
    )
    provision_amount = fields.Monetary(
        string="Default Provision Amount", currency_field="company_currency_id"
    )
    account_id = fields.Many2one(
        "account.account",
        string="Account",
        required=True,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
    )
    tax_ids = fields.Many2many(
        "account.tax",
        string="Taxes",
        domain="[('price_include', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
    )

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

    @api.onchange("min_amount")
    def min_amount_change(self):
        if self.min_amount > 0 and not self.provision_amount:
            self.provision_amount = self.min_amount

    @api.onchange("account_id")
    def account_id_change(self):
        if self.account_id:
            self.tax_ids = self.account_id.tax_ids

    @api.onchange("partner_type")
    def partner_type_change(self):
        if self.partner_type != "one":
            self.partner_id = False

    def _process_subscription(self, work, end_date, common_domain, sign):
        self.ensure_one()
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
            ("analytic_account_id", "=", self.analytic_account_id.id or False),
        ]
        if self.partner_type == "one":
            if self.partner_id:
                domain_base.append(("partner_id", "=", self.partner_id.id))
            else:
                raise UserError(
                    _("Missing supplier on subscription '%s'.") % self.display_name
                )
        elif self.partner_type == "none":
            domain_base.append(("partner_id", "=", False))
        domain_base_w_start_end = domain_base + [
            ("start_date", "!=", False),
            ("end_date", "!=", False),
        ]

        for _i in range(int(12 / months)):
            start_date = end_date + relativedelta(day=1, months=-(months - 1))
            if start_date < self.start_date:
                break
            # compute amount
            amount = 0
            # 1. No start/end dates
            no_start_end_res = aml_obj.read_group(
                domain_base
                + [
                    ("date", "<=", end_date),
                    ("date", ">=", start_date),
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

            work[self]["intervals"].append(
                {
                    "start": start_date,
                    "end": end_date,
                    "amount": ccur.round(amount),
                }
            )
            # prepare next interval
            end_date = start_date + relativedelta(days=-1)
