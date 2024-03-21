# Copyright 2013-2021 Akretion (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import date_utils


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
    # technical field to filter taxes on lines
    # (and source_journal_ids in account_cutoff_start_end_dates)
    filter_type_domain = fields.Char(compute="_compute_filter_type_domain")
    show_taxes = fields.Boolean(compute="_compute_show_taxes")
    source_move_state = fields.Selection(
        [("posted", "Posted Entries"), ("draft_posted", "Draft and Posted Entries")],
        string="Source Entries",
        required=True,
        default="posted",
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
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
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
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
        related="company_id.currency_id",
        string="Company Currency",
        store=True,
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

    @api.depends("cutoff_type")
    def _compute_filter_type_domain(self):
        domain_map = {
            "accrued_revenue": "sale",
            "prepaid_revenue": "sale",
            "accrued_expense": "purchase",
            "prepaid_expense": "purchase",
        }
        for rec in self:
            rec.filter_type_domain = domain_map.get(rec.cutoff_type)

    @api.depends("company_id.accrual_taxes", "cutoff_type")
    def _compute_show_taxes(self):
        for rec in self:
            show_taxes = False
            if rec.company_id.accrual_taxes and rec.cutoff_type in (
                "accrued_revenue",
                "accrued_expense",
            ):
                show_taxes = True
            rec.show_taxes = show_taxes

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
        if self.company_id.post_cutoff_move:
            move._post(soft=False)
        self.write({"move_id": move.id, "state": "done"})
        self.message_post(body=_("Journal entry generated"))

        xmlid = "account.action_move_journal_line"
        action = self.env["ir.actions.act_window"]._for_xml_id(xmlid)
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
        # Delete existing automatic lines
        self.line_ids.filtered(lambda x: not x.manual).unlink()
        self.message_post(body=_("Cut-off lines re-generated"))

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
        xmlid = "account_cutoff_base.account_cutoff_line_action"
        action = self.env["ir.actions.act_window"]._for_xml_id(xmlid)
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
        mappings = self.env["account.cutoff.mapping"].search_read(
            [
                ("company_id", "=", self.company_id.id),
                ("cutoff_type", "in", ("all", self.cutoff_type)),
            ],
            ["account_id", "cutoff_account_id"],
        )
        mapping = {}
        for item in mappings:
            mapping[item["account_id"][0]] = item["cutoff_account_id"][0]
        return mapping


class AccountCutoffLine(models.Model):
    _name = "account.cutoff.line"
    _description = "Account Cut-off Line"
    _check_company_auto = True

    parent_id = fields.Many2one("account.cutoff", string="Cut-off", ondelete="cascade")
    # field used to delete only automatic lines when clicking on "Re-generate lines"
    manual = fields.Boolean(default=True)
    name = fields.Char(string="Description", states={"done": [("readonly", True)]})
    company_currency_id = fields.Many2one(
        related="parent_id.company_currency_id",
        string="Company Currency",
        store=True,
    )
    company_id = fields.Many2one(related="parent_id.company_id", store=True)
    cutoff_type = fields.Selection(related="parent_id.cutoff_type")
    filter_type_domain = fields.Char(related="parent_id.filter_type_domain")
    show_taxes = fields.Boolean(related="parent_id.show_taxes")
    state = fields.Selection(related="parent_id.state", store=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        states={"done": [("readonly", True)]},
        domain="[('parent_id', '=', False)]",
        check_company=True,
    )
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
        "account.move.line",
        string="Origin Journal Item",
        readonly=True,
        check_company=True,
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
        required=False,
        states={"done": [("readonly", True)]},
        check_company=True,
        domain="[('company_id', '=', company_id), ('deprecated', '=', False)]",
    )
    cutoff_account_id = fields.Many2one(
        "account.account",
        string="Cut-off Account",
        compute="_compute_cutoff_account_id",
        store=True,
        readonly=False,
        check_company=True,
        required=True,
        states={"done": [("readonly", True)]},
    )
    cutoff_account_code = fields.Char(
        related="cutoff_account_id.code",
        string="Cut-off Account Code",
        store=True,
    )
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        states={"done": [("readonly", True)]},
        check_company=True,
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
        required=True,
        states={"done": [("readonly", True)]},
        help="Cut-off amount without taxes in the company currency. "
        "Negative amounts will become a debit on the provision line ; "
        "positive amounts will become a credit on the provision line.",
    )
    tax_ids = fields.Many2many(
        "account.tax",
        string="Taxes",
        check_company=True,
        context={"active_test": False},
        domain="[('company_id', '=', company_id), ('type_tax_use', '=', filter_type_domain)]",
        states={"done": [("readonly", True)]},
    )
    tax_line_ids = fields.One2many(
        "account.cutoff.tax.line",
        "parent_id",
        compute="_compute_tax_line_ids",
        store=True,
        string="Cut-off Tax Lines",
    )
    notes = fields.Text()

    @api.constrains("tax_ids")
    def _check_tax_ids(self):
        for line in self:
            cutoff_type = line.parent_id.cutoff_type
            for tax in line.tax_ids:
                if cutoff_type == "accrued_expense":
                    if not tax.account_accrued_expense_id:
                        raise ValidationError(
                            _("Missing Accrued Expense Tax Account on tax %s.")
                            % tax.display_name
                        )
                elif cutoff_type == "accrued_revenue":
                    if not tax.account_accrued_revenue_id:
                        raise ValidationError(
                            _("Missing Accrued Revenue Tax Account on tax %s.")
                            % tax.display_name
                        )

    @api.depends("parent_id.cutoff_type", "account_id")
    def _compute_cutoff_account_id(self):
        for line in self:
            parent = line.parent_id
            cutoff_account_id = line.account_id.id
            if line.account_id and parent:
                mapping = parent._get_mapping_dict()
                if line.account_id.id in mapping:
                    cutoff_account_id = mapping[line.account_id.id]
            line.cutoff_account_id = cutoff_account_id

    @api.depends("tax_ids", "cutoff_amount", "company_id")
    def _compute_tax_line_ids(self):
        ato = self.env["account.tax"]
        for line in self:
            cutoff_type = line.parent_id.cutoff_type
            if (
                line.company_id.accrual_taxes
                and cutoff_type in ("accrued_expense", "accrued_revenue")
                and line.tax_ids
            ):
                tax_line_ids = [(5,)]
                tax_compute_all_res = line.tax_ids.compute_all(
                    line.cutoff_amount, handle_price_include=False
                )
                company_currency = line.company_currency_id
                for tax_line in tax_compute_all_res.get("taxes", []):
                    if company_currency.is_zero(tax_line.get("amount", 0)):
                        continue
                    tax = ato.browse(tax_line["id"] or tax_line["id"].origin)
                    if cutoff_type == "accrued_expense":
                        tax_accrual_account_id = tax.account_accrued_expense_id.id
                    elif cutoff_type == "accrued_revenue":
                        tax_accrual_account_id = tax.account_accrued_revenue_id.id
                    else:
                        continue  # should never happen
                    tax_line_ids.append(
                        (
                            0,
                            0,
                            {
                                # TODO analytic ?
                                "tax_id": tax.id,
                                "base": company_currency.round(tax_line["base"]),
                                "sequence": tax_line["sequence"],
                                "cutoff_account_id": tax_accrual_account_id,
                                "cutoff_amount": company_currency.round(
                                    tax_line["amount"]
                                ),
                            },
                        )
                    )
                line.tax_line_ids = tax_line_ids
            else:
                line.tax_line_ids = [(5,)]


class AccountCutoffTaxLine(models.Model):
    _name = "account.cutoff.tax.line"
    _description = "Account Cut-off Tax Line"
    # All the fields of cutoff tax lines are in company currency

    cutoff_id = fields.Many2one(
        "account.cutoff", related="parent_id.parent_id", store=True
    )
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
        currency_field="company_currency_id",
        readonly=True,
        help="Base Amount in the company currency.",
    )
    sequence = fields.Integer(readonly=True)
    cutoff_amount = fields.Monetary(
        string="Cut-off Tax Amount",
        currency_field="company_currency_id",
        readonly=True,
        help="Tax Cut-off Amount in the company currency.",
    )
    company_currency_id = fields.Many2one(
        related="parent_id.company_currency_id",
        string="Company Currency",
        store=True,
    )
