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
    code_start = fields.Char(
        string="Start Account Code",
        required=True,
    )
    code_end = fields.Char(
        string="End Account Code",
        required=True,
    )
    dest_account_code = fields.Char(
        string="Destination Account Code",
        required=True,
        help="The code of the destination account (e.g., 3.1.01.001)",
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

    @api.onchange("code_start", "code_end")
    def _onchange_code_range(self):
        """Update preview accounts when code range changes."""
        if not (self.code_start and self.code_end):
            self.preview_account_ids = False
            return

        try:
            if self.fyc_config_id:
                company_id = self.fyc_config_id.fyc_id.company_id.id
            elif (
                self.fyc_config_template_id and self.fyc_config_template_id.template_id
            ):
                company_id = self.env.company.id
            else:
                company_id = self.env.company.id
        except AttributeError:
            company_id = self.env.company.id

        domain = [
            ("company_ids", "in", [company_id]),
            ("code", ">=", self.code_start),
            ("code", "<=", self.code_end),
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
            dest_acc = self.env["account.account"].search(
                [
                    ("code", "=", self.dest_account_code),
                    ("company_ids", "in", [self.fyc_config_id.fyc_id.company_id.id]),
                ],
                limit=1,
            )

            vals.update(
                {
                    "fyc_config_id": self.fyc_config_id.id,
                    "dest_account_id": dest_acc.id,
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

        if not self.preview_account_ids:
            raise UserError(_("No accounts found in the selected range."))

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
                    "code": self.dest_account_code,
                },
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def action_cancel(self):
        """Close the wizard window."""
        return {"type": "ir.actions.act_window_close"}
