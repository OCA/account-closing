# Copyright 2025 Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FiscalYearClosingRangeWizard(models.TransientModel):
    _name = "fiscalyear.closing.range.wizard"
    _description = "Wizard for generating account range mappings in fiscal year closing"

    fyc_config_id = fields.Many2one(
        comodel_name="account.fiscalyear.closing.config",
        string="Fiscal Year Closing Config",
    )
    fyc_config_template_id = fields.Many2one(
        comodel_name="account.fiscalyear.closing.config.template",
        string="Fiscal Year Closing Config Template",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        compute="_compute_company_id",
        store=True,
    )
    account_start_id = fields.Many2one(
        comodel_name="account.account",
        string="Start Account",
        domain="[('company_ids', 'in', [company_id])]",
        required=True,
    )
    account_end_id = fields.Many2one(
        comodel_name="account.account",
        string="End Account",
        domain="[('company_ids', 'in', [company_id])]",
        required=True,
    )
    dest_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Destination Account",
        domain="[('company_ids', 'in', [company_id])]",
        help="The destination account where the balance will be transferred to.",
    )
    dest_account_code = fields.Char(
        string="Destination Account Code",
        help="The code of the destination account (e.g., 3.1.01.001). "
        "Used for templates, which are not tied to a single company.",
    )
    preview_account_ids = fields.Many2many(
        comodel_name="account.account",
        string="Preview Accounts",
        readonly=True,
    )
    name_prefix = fields.Char(
        string="Mapping Name Prefix",
    )

    @api.depends("fyc_config_id", "fyc_config_template_id")
    def _compute_company_id(self):
        for record in self:
            if record.fyc_config_id:
                record.company_id = record.fyc_config_id.fyc_id.company_id
            else:
                record.company_id = self.env.company

    @api.onchange("account_start_id", "account_end_id")
    def _onchange_code_range(self):
        """Update preview accounts when the account range changes."""
        if not (self.account_start_id and self.account_end_id):
            self.preview_account_ids = False
            return

        company_id = self.company_id.id or self.env.company.id

        domain = [
            ("company_ids", "in", [company_id]),
            ("code", ">=", self.account_start_id.code),
            ("code", "<=", self.account_end_id.code),
        ]
        self.preview_account_ids = self.env["account.account"].search(
            domain, order="code ASC"
        )

    def _prepare_mapping_vals(self, account):
        """Helper to prepare the dictionary for creation."""
        name = f"{account.code} - {account.name}"
        if self.name_prefix:
            name = f"{self.name_prefix} - {name}"

        vals = {
            "src_accounts": account.code,
            "name": name,
        }

        if self.fyc_config_id:
            vals.update(
                {
                    "fyc_config_id": self.fyc_config_id.id,
                    "dest_account_id": self.dest_account_id.id,
                }
            )
        else:
            vals.update(
                {
                    "template_config_id": self.fyc_config_template_id.id,
                    "dest_account": self.dest_account_code,
                }
            )
        return vals

    def action_apply(self):
        self.ensure_one()

        if not (self.fyc_config_id or self.fyc_config_template_id):
            raise UserError(
                _(
                    "This wizard must be opened from a fiscal year closing "
                    "configuration or template."
                )
            )

        if not self.preview_account_ids:
            raise UserError(_("No accounts found in the selected range."))

        if self.fyc_config_id and not self.dest_account_id:
            raise UserError(_("Please select a destination account."))

        if not self.fyc_config_id and not self.dest_account_code:
            raise UserError(_("Please enter a destination account code."))

        if self.fyc_config_template_id and not self.fyc_config_template_id.template_id:
            raise UserError(
                _(
                    "Cannot generate range mappings: The fiscal year closing "
                    "template is not properly linked to a parent template."
                    "This usually happens when trying to use the wizard before saving "
                    "the template. Please save the template first and try again."
                )
            )

        vals_list = [
            self._prepare_mapping_vals(acc) for acc in self.preview_account_ids
        ]

        model_name = (
            "account.fiscalyear.closing.mapping"
            if self.fyc_config_id
            else "account.fiscalyear.closing.mapping.template"
        )

        created_records = self.env[model_name].create(vals_list)

        dest_code = (
            self.dest_account_id.code if self.fyc_config_id else self.dest_account_code
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Success"),
                "message": _(
                    "%(count)d mapping lines created using destination code %(code)s."
                )
                % {
                    "count": len(created_records),
                    "code": dest_code,
                },
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def action_cancel(self):
        """Close the wizard window."""
        return {"type": "ir.actions.act_window_close"}
