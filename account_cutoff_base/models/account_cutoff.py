# Copyright 2013-2021 Akretion (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import date_utils, float_is_zero


class AccountCutoff(models.Model):
    _name = "account.cutoff"
    _rec_name = "cutoff_date"
    _order = "cutoff_date desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _check_company_auto = True
    _description = "Account Cut-off"

    @api.depends("line_ids", "line_ids.cutoff_amount")
    def _compute_total_cutoff(self):
        rg_res = self.env["account.cutoff.line"].read_group(
            [("parent_id", "in", self.ids)],
            ["parent_id", "cutoff_amount"],
            ["parent_id"],
        )
        mapped_data = {x["parent_id"][0]: x["cutoff_amount"] for x in rg_res}
        for cutoff in self:
            cutoff.total_cutoff_amount = mapped_data.get(cutoff.id, 0)

    @property
    def cutoff_type_label_map(self):
        return {
            "accrued_expense": _("Accrued Expense"),
            "accrued_revenue": _("Accrued Revenue"),
            "prepaid_revenue": _("Prepaid Revenue"),
            "prepaid_expense": _("Prepaid Expense"),
        }

    @api.model
    def _default_move_label(self):
        cutoff_type = self.env.context.get("default_cutoff_type")
        label = self.cutoff_type_label_map.get(cutoff_type, "")
        return label

    @api.model
    def _default_cutoff_date(self):
        today = fields.Date.context_today(self)
        company = self.env.company
        date_from, date_to = date_utils.get_fiscal_year(
            today,
            day=company.fiscalyear_last_day,
            month=int(company.fiscalyear_last_month),
        )
        if date_from:
            return date_from - relativedelta(days=1)
        else:
            return False

    def _selection_cutoff_type(self):
        # generate cutoff types from mapping
        return list(self.cutoff_type_label_map.items())

    @api.model
    def _default_cutoff_account_id(self):
        cutoff_type = self.env.context.get("default_cutoff_type")
        company = self.env.company
        if cutoff_type == "accrued_expense":
            account_id = company.default_accrued_expense_account_id.id or False
        elif cutoff_type == "accrued_revenue":
            account_id = company.default_accrued_revenue_account_id.id or False
        elif cutoff_type == "prepaid_revenue":
            account_id = company.default_prepaid_revenue_account_id.id or False
        elif cutoff_type == "prepaid_expense":
            account_id = company.default_prepaid_expense_account_id.id or False
        else:
            account_id = False
        return account_id

    cutoff_date = fields.Date(
        string="Cut-off Date",
        readonly=True,
        states={"draft": [("readonly", False)]},
        copy=False,
        tracking=True,
        default=lambda self: self._default_cutoff_date(),
    )
    cutoff_type = fields.Selection(
        selection="_selection_cutoff_type",
        string="Type",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    move_id = fields.Many2one(
        "account.move",
        string="Cut-off Journal Entry",
        readonly=True,
        copy=False,
        check_company=True,
    )
    move_label = fields.Char(
        string="Label of the Cut-off Journal Entry",
        readonly=True,
        states={"draft": [("readonly", False)]},
        default=lambda self: self._default_move_label(),
        help="This label will be written in the 'Name' field of the "
        "Cut-off Account Move Lines and in the 'Reference' field of "
        "the Cut-off Account Move.",
    )
    move_partner = fields.Boolean(
        string="Partner on Move Line",
        default=lambda self: self.env.company.default_cutoff_move_partner,
    )
    cutoff_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Cut-off Account",
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        readonly=True,
        states={"draft": [("readonly", False)]},
        default=lambda self: self._default_cutoff_account_id(),
        check_company=True,
        tracking=True,
    )
    cutoff_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Cut-off Account Journal",
        default=lambda self: self.env.company.default_cutoff_journal_id,
        readonly=True,
        states={"draft": [("readonly", False)]},
        domain="[('company_id', '=', company_id)]",
        check_company=True,
        tracking=True,
    )
    total_cutoff_amount = fields.Monetary(
        compute="_compute_total_cutoff",
        string="Total Cut-off Amount",
        currency_field="company_currency_id",
        readonly=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        default=lambda self: self.env.company,
    )
    company_currency_id = fields.Many2one(
        related="company_id.currency_id", string="Company Currency"
    )
    line_ids = fields.One2many(
        comodel_name="account.cutoff.line",
        inverse_name="parent_id",
        string="Cut-off Lines",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    state = fields.Selection(
        selection=[("draft", "Draft"), ("done", "Done")],
        index=True,
        readonly=True,
        tracking=True,
        default="draft",
        copy=False,
        help="State of the cutoff. When the Journal Entry is created, "
        "the state is set to 'Done' and the fields become read-only.",
    )

    _sql_constraints = [
        (
            "date_type_company_uniq",
            "unique(cutoff_date, company_id, cutoff_type)",
            _("A cutoff of the same type already exists with this cut-off date !"),
        )
    ]

    def back2draft(self):
        self.ensure_one()
        if self.move_id:
            self.move_id.unlink()
        self.write({"state": "draft"})

    def _get_merge_keys(self):
        """Return merge criteria for provision lines

        The returned list must contain valid field names
        for account.move.line. Provision lines with the
        same values for these fields will be merged.
        The list must at least contain account_id.
        """
        return ["partner_id", "account_id", "analytic_account_id"]

    def _prepare_move(self, to_provision):
        self.ensure_one()
        movelines_to_create = []
        amount_total = 0
        move_label = self.move_label
        merge_keys = self._get_merge_keys()
        for merge_values, amount in to_provision.items():
            amount = self.company_currency_id.round(amount)
            vals = {
                "debit": amount < 0 and amount * -1 or 0,
                "credit": amount >= 0 and amount or 0,
            }
            for k, v in zip(merge_keys, merge_values):
                vals[k] = v
            movelines_to_create.append((0, 0, vals))
            amount_total += amount

        # add counter-part
        counterpart_amount = self.company_currency_id.round(amount_total * -1)
        movelines_to_create.append(
            (
                0,
                0,
                {
                    "account_id": self.cutoff_account_id.id,
                    "debit": counterpart_amount < 0 and counterpart_amount * -1 or 0,
                    "credit": counterpart_amount >= 0 and counterpart_amount or 0,
                    "analytic_account_id": False,
                },
            )
        )

        res = {
            "company_id": self.company_id.id,
            "journal_id": self.cutoff_journal_id.id,
            "date": self.cutoff_date,
            "ref": move_label,
            "line_ids": movelines_to_create,
        }
        return res

    def _prepare_provision_line(self, cutoff_line):
        """Convert a cutoff line to elements of a move line.

        The returned dictionary must at least contain 'account_id'
        and 'amount' (< 0 means debit).

        If you override this, the added fields must also be
        added in an override of _get_merge_keys.
        """
        partner_id = cutoff_line.partner_id.id or False
        return {
            "partner_id": self.move_partner and partner_id or False,
            "account_id": cutoff_line.cutoff_account_id.id,
            "analytic_account_id": cutoff_line.analytic_account_id.id,
            "amount": cutoff_line.cutoff_amount,
        }

    def _prepare_provision_tax_line(self, cutoff_tax_line):
        """Convert a cutoff tax line to elements of a move line.

        See _prepare_provision_line for more info.
        """
        return {
            "partner_id": False,
            "account_id": cutoff_tax_line.cutoff_account_id.id,
            "analytic_account_id": cutoff_tax_line.analytic_account_id.id,
            "amount": cutoff_tax_line.cutoff_amount,
        }

    def _merge_provision_lines(self, provision_lines):
        """Merge provision line.

        Returns a dictionary {key, amount} where key is
        a tuple containing the values of the properties in _get_merge_keys()
        """
        to_provision = defaultdict(float)
        merge_keys = self._get_merge_keys()
        for provision_line in provision_lines:
            key = tuple([provision_line.get(key) for key in merge_keys])
            to_provision[key] += provision_line["amount"]
        return to_provision

    def create_move(self):
        self.ensure_one()
        move_obj = self.env["account.move"]
        if self.move_id:
            raise UserError(
                _(
                    "The Cut-off Journal Entry already exists. You should "
                    "delete it before running this function."
                )
            )
        if not self.line_ids:
            raise UserError(
                _(
                    "There are no lines on this Cut-off, so we can't create "
                    "a Journal Entry."
                )
            )
        provision_lines = []
        for line in self.line_ids:
            provision_lines.append(self._prepare_provision_line(line))
            for tax_line in line.tax_line_ids:
                provision_lines.append(self._prepare_provision_tax_line(tax_line))
        to_provision = self._merge_provision_lines(provision_lines)
        vals = self._prepare_move(to_provision)
        move = move_obj.create(vals)
        self.write({"move_id": move.id, "state": "done"})
        self.message_post(body=_("Journal entry generated"))

        action = self.env.ref("account.action_move_journal_line").sudo().read()[0]
        action.update(
            {
                "view_mode": "form,tree",
                "res_id": move.id,
                "view_id": False,
                "views": False,
            }
        )
        return action

    def get_lines(self):
        """This method is designed to be inherited in other modules"""
        self.ensure_one()
        # Delete existing lines
        self.line_ids.unlink()
        self.message_post(body=_("Cut-off lines re-generated"))
        return True

    def unlink(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(
                    _(
                        "You cannot delete cutoff records that are not "
                        "in draft state."
                    )
                )
        return super().unlink()

    def button_line_tree(self):
        action = (
            self.env.ref("account_cutoff_base.account_cutoff_line_action")
            .sudo()
            .read()[0]
        )
        action.update(
            {
                "domain": [("parent_id", "=", self.id)],
                "views": False,
            }
        )
        return action

    def _get_mapping_dict(self):
        """return a dict with:
        key = ID of account,
        value = ID of cutoff_account"""
        self.ensure_one()
        mappings = self.env["account.cutoff.mapping"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("cutoff_type", "in", ("all", self.cutoff_type)),
            ]
        )
        mapping = {}
        for item in mappings:
            mapping[item.account_id.id] = item.cutoff_account_id.id
        return mapping

    def _prepare_tax_lines(self, tax_compute_all_res, currency):
        res = []
        ato = self.env["account.tax"]
        company_currency = self.company_id.currency_id
        cur_rprec = company_currency.rounding
        for tax_line in tax_compute_all_res["taxes"]:
            tax = ato.browse(tax_line["id"])
            if float_is_zero(tax_line["amount"], precision_rounding=cur_rprec):
                continue
            if self.cutoff_type == "accrued_expense":
                tax_accrual_account_id = tax.account_accrued_expense_id.id
                tax_account_field_label = _("Accrued Expense Tax Account")
            elif self.cutoff_type == "accrued_revenue":
                tax_accrual_account_id = tax.account_accrued_revenue_id.id
                tax_account_field_label = _("Accrued Revenue Tax Account")
            if not tax_accrual_account_id:
                raise UserError(
                    _("Missing '%s' on tax '%s'.")
                    % (tax_account_field_label, tax.display_name)
                )
            tax_amount = currency.round(tax_line["amount"])
            tax_accrual_amount = currency._convert(
                tax_amount, company_currency, self.company_id, self.cutoff_date
            )
            res.append(
                (
                    0,
                    0,
                    {
                        "tax_id": tax_line["id"],
                        "base": tax_line["base"],  # in currency
                        "amount": tax_amount,  # in currency
                        "sequence": tax_line["sequence"],
                        "cutoff_account_id": tax_accrual_account_id,
                        "cutoff_amount": tax_accrual_amount,  # in company currency
                    },
                )
            )
        return res


class AccountCutoffLine(models.Model):
    _name = "account.cutoff.line"
    _description = "Account Cut-off Line"

    parent_id = fields.Many2one("account.cutoff", string="Cut-off", ondelete="cascade")
    name = fields.Char("Description")
    company_currency_id = fields.Many2one(
        related="parent_id.company_currency_id",
        string="Company Currency",
        readonly=True,
    )
    partner_id = fields.Many2one("res.partner", string="Partner", readonly=True)
    quantity = fields.Float(
        string="Quantity", digits="Product Unit of Measure", readonly=True
    )
    price_unit = fields.Float(
        string="Unit Price w/o Tax",
        digits="Product Price",
        readonly=True,
        help="Price per unit (discount included) without taxes in the default "
        "unit of measure of the product in the currency of the 'Currency' field.",
    )
    price_origin = fields.Char(readonly=True)
    origin_move_line_id = fields.Many2one(
        "account.move.line", string="Origin Journal Item", readonly=True
    )  # Old name: move_line_id
    origin_move_id = fields.Many2one(
        related="origin_move_line_id.move_id", string="Origin Journal Entry"
    )  # old name: move_id
    origin_move_date = fields.Date(
        related="origin_move_line_id.move_id.date", string="Origin Journal Entry Date"
    )  # old name: move_date
    account_id = fields.Many2one(
        "account.account",
        "Account",
        required=True,
        readonly=True,
    )
    cutoff_account_id = fields.Many2one(
        "account.account",
        string="Cut-off Account",
        required=True,
        readonly=True,
    )
    cutoff_account_code = fields.Char(
        related="cutoff_account_id.code", string="Cut-off Account Code", readonly=True
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Amount Currency",
        readonly=True,
        help="Currency of the 'Amount' field.",
    )
    amount = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
        help="Amount that is used as base to compute the Cut-off Amount. "
        "This Amount is in the 'Amount Currency', which may be different "
        "from the 'Company Currency'.",
    )
    cutoff_amount = fields.Monetary(
        string="Cut-off Amount",
        currency_field="company_currency_id",
        readonly=True,
        help="Cut-off Amount without taxes in the Company Currency.",
    )
    tax_line_ids = fields.One2many(
        "account.cutoff.tax.line",
        "parent_id",
        string="Cut-off Tax Lines",
        readonly=True,
    )
    notes = fields.Text()


class AccountCutoffTaxLine(models.Model):
    _name = "account.cutoff.tax.line"
    _description = "Account Cut-off Tax Line"

    parent_id = fields.Many2one(
        "account.cutoff.line",
        string="Account Cut-off Line",
        ondelete="cascade",
        required=True,
    )
    tax_id = fields.Many2one("account.tax", string="Tax", required=True)
    cutoff_account_id = fields.Many2one(
        "account.account",
        string="Cut-off Account",
        required=True,
        readonly=True,
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        readonly=True,
    )
    base = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
        help="Base Amount in the currency of the PO.",
    )
    amount = fields.Monetary(
        string="Tax Amount",
        currency_field="currency_id",
        readonly=True,
        help="Tax Amount in the currency of the PO.",
    )
    sequence = fields.Integer(readonly=True)
    cutoff_amount = fields.Monetary(
        string="Cut-off Tax Amount",
        currency_field="company_currency_id",
        readonly=True,
        help="Tax Cut-off Amount in the company currency.",
    )
    currency_id = fields.Many2one(
        related="parent_id.currency_id", string="Currency", readonly=True
    )
    company_currency_id = fields.Many2one(
        related="parent_id.company_currency_id",
        string="Company Currency",
        readonly=True,
    )
