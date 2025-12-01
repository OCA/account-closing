# Copyright 2025 Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
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

    @api.model
    def create(self, vals):
        if "dest_account_id" in vals and isinstance(vals["dest_account_id"], int):
            vals["dest_account_id"] = [vals["dest_account_id"]]
        return super().create(vals)

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
        domain = [("company_id", "=", self.fyc_id.company_id.id)]

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

    def _mapping_move_lines_get(self):
        """
        Retrieve move lines for the closing entry.
        Overridden to support account filtering by range (Start/End)
        in addition to the standard pattern matching.
        """
        move_lines = []
        dest_totals = {}

        for account_map in self.mapping_ids:
            dest = account_map.dest_account_id
            dest_totals.setdefault(dest, 0.0)

            domain = self._get_mapping_account_domain(account_map)
            if not domain:
                continue

            src_accounts = self.env["account.account"].search(domain, order="code ASC")

            for account in src_accounts:
                closing_type = self.closing_type_get(account)
                balance = 0.0
                move_line = {}

                if closing_type == "balance":
                    lines = account_map.account_lines_get(account)
                    balance, move_line = account_map.move_line_prepare(account, lines)
                    if move_line:
                        move_lines.append(move_line)

                elif closing_type == "unreconciled":
                    partners = account_map.account_partners_get(account)
                    for partner in partners:
                        balance, move_line = account_map.move_line_partner_prepare(
                            account, partner
                        )
                        if move_line:
                            move_lines.append(move_line)

                if dest and balance:
                    dest_totals[dest] -= balance

        for account_map in self.mapping_ids.filtered("dest_account_id"):
            dest = account_map.dest_account_id
            balance = dest_totals.get(dest, 0.0)

            if not balance:
                continue

            dest_totals[dest] = 0.0
            move_line = account_map.dest_move_line_prepare(dest, balance)
            if move_line:
                move_lines.append(move_line)

        return move_lines
