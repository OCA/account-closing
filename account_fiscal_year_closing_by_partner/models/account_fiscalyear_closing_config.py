from odoo import models
from odoo.tools import float_is_zero

_PARTNER_ACCOUNT_TYPES = ("asset_receivable", "liability_payable")


class AccountFiscalyearClosingConfig(models.Model):
    _inherit = "account.fiscalyear.closing.config"

    def _split_closing_lines_by_partner(self):
        """Split aggregate lines for receivable/payable accounts into per-partner
        lines. Dispatches to the appropriate method based on config type."""
        self.ensure_one()
        move = self.move_id
        if not move:
            return
        if self.mapping_ids:
            self._split_partner_lines_from_mappings(move)
        elif self.inverse:
            self._split_partner_lines_from_closing(move)

    def _split_partner_lines_from_mappings(self, move):
        """Replace aggregate closing lines for receivable/payable accounts with
        per-partner lines. Called after the closing move has been created.

        We mirror exactly what account_lines_get returns (same domain + same
        debit/credit computation as move_line_prepare) so the per-partner
        totals always equal the aggregate — keeping the journal entry balanced.
        We exclude FYC closing moves (move_id.fyc_id is set) to avoid picking
        up the aggregate line we just created in the current FYC pass."""
        precision = self.env["decimal.precision"].precision_get("Account")
        fyc = self.fyc_id

        for acc_map in self.mapping_ids:
            src_accounts = self.env["account.account"].search(
                [
                    ("company_ids", "in", fyc.company_id.ids),
                    ("code", "=ilike", acc_map.src_accounts),
                ],
                order="code ASC",
            )
            for account in src_accounts:
                if account.account_type not in _PARTNER_ACCOUNT_TYPES:
                    continue

                agg_lines = move.line_ids.filtered(
                    lambda ln, acc=account: ln.account_id == acc
                )
                if not agg_lines:
                    continue

                # Use the same lines as account_lines_get (state != cancel, in
                # date range), but exclude lines that belong to FYC closing
                # moves — those didn't exist when the aggregate was computed.
                src_lines = acc_map.account_lines_get(account).filtered(
                    lambda ln: not ln.move_id.fyc_id
                )
                if not src_lines:
                    continue

                # Group by partner, compute debit/credit the same way as
                # move_line_prepare does (balance = SUM(debit) - SUM(credit)).
                partner_groups = {}
                for line in src_lines:
                    pid = line.partner_id.id if line.partner_id else False
                    partner_groups.setdefault(pid, {"debit": 0.0, "credit": 0.0})
                    partner_groups[pid]["debit"] += line.debit
                    partner_groups[pid]["credit"] += line.credit

                date = fyc.date_end
                if self.move_type == "opening":
                    date = fyc.date_opening
                description = acc_map.name or account.name

                new_line_vals = []
                ordered_partners = []
                for pid, totals in partner_groups.items():
                    balance = totals["debit"] - totals["credit"]
                    if float_is_zero(balance, precision_digits=precision):
                        continue
                    new_line_vals.append(
                        {
                            "account_id": account.id,
                            "debit": balance < 0 and -balance,
                            "credit": balance > 0 and balance,
                            "name": description,
                            "date": date,
                        }
                    )
                    ordered_partners.append(pid)

                if not new_line_vals:
                    continue

                # Delete aggregate + create per-partner in one write so that
                # _check_balanced runs once at the very end (balanced by design:
                # per-partner totals == aggregate total from same source lines).
                commands = [(3, line.id) for line in agg_lines]
                commands += [(0, 0, vals) for vals in new_line_vals]
                move.write({"line_ids": commands})

                # Write partner_id after creation.  The precompute derives
                # partner_id from move_id.partner_id (False for FYC entries)
                # and would clear it, so we set it explicitly here instead.
                new_lines = move.line_ids.filtered(
                    lambda ln, acc=account: ln.account_id == acc
                ).sorted("id")
                for partner_id, line in zip(ordered_partners, new_lines, strict=False):
                    if partner_id:
                        line.partner_id = partner_id

    def _split_partner_lines_from_closing(self, move):
        """Split opening move lines by partner, mirroring the already-split
        closing move. Opening lines are the exact reversal of closing lines
        (debit ↔ credit), so we read the closing move's per-partner lines and
        create the symmetric counterparts in the opening move."""
        closing_config = self.config_inverse_get()
        if not closing_config or not closing_config.move_id:
            return
        closing_move = closing_config.move_id

        partner_accounts = closing_move.line_ids.filtered(
            lambda ln: ln.account_id.account_type in _PARTNER_ACCOUNT_TYPES
            and ln.partner_id
        ).mapped("account_id")

        for account in partner_accounts:
            closing_partner_lines = closing_move.line_ids.filtered(
                lambda ln, acc=account: ln.account_id == acc and ln.partner_id
            )
            if not closing_partner_lines:
                continue

            agg_lines = move.line_ids.filtered(
                lambda ln, acc=account: ln.account_id == acc
            )
            if not agg_lines:
                continue

            new_line_vals = []
            ordered_partners = []
            for cl in closing_partner_lines:
                new_line_vals.append(
                    {
                        "account_id": account.id,
                        "debit": cl.credit,
                        "credit": cl.debit,
                        "name": agg_lines[0].name,
                        "date": move.date,
                    }
                )
                ordered_partners.append(cl.partner_id.id)

            commands = [(3, line.id) for line in agg_lines]
            commands += [(0, 0, vals) for vals in new_line_vals]
            move.write({"line_ids": commands})

            new_lines = move.line_ids.filtered(
                lambda ln, acc=account: ln.account_id == acc
            ).sorted("id")
            for partner_id, line in zip(ordered_partners, new_lines, strict=False):
                line.partner_id = partner_id
