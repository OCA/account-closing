# Copyright 2026 Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountFiscalyearClosingMapping(models.Model):
    _inherit = "account.fiscalyear.closing.mapping"

    code_start = fields.Char(
        string="Start Account Code",
    )
    code_end = fields.Char(
        string="End Account Code",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "dest_account_id" in vals and isinstance(vals["dest_account_id"], int):
                vals["dest_account_id"] = [vals["dest_account_id"]]
        return super().create(vals_list)

    def write(self, vals):
        if "dest_account_id" in vals and isinstance(vals["dest_account_id"], int):
            vals["dest_account_id"] = [vals["dest_account_id"]]
        return super().write(vals)


class AccountFiscalyearClosingConfig(models.Model):
    _inherit = "account.fiscalyear.closing.config"

    def _get_mapping_account_domain(self, mapping):
        """
        Construct the search domain for accounts based on range or pattern.
        Returns None if no valid configuration is found.
        """
        domain = [("company_ids", "in", [self.fyc_id.company_id.id])]

        if mapping.code_start and mapping.code_end:
            domain += [
                ("code", ">=", mapping.code_start),
                ("code", "<=", mapping.code_end),
            ]
        elif mapping.src_accounts:
            domain += [("code", "=ilike", mapping.src_accounts)]
        else:
            return None

        return domain

    def _mapping_src_accounts_get(self, account_map):
        """Select the source accounts supporting filtering by range
        (Start/End) in addition to the standard pattern matching.

        Only the account selection is overridden here; the move-line
        generation (including the per-partner split) is inherited from
        account_fiscal_year_closing.
        """
        domain = self._get_mapping_account_domain(account_map)
        if not domain:
            return self.env["account.account"]
        return self.env["account.account"].search(domain, order="code ASC")
