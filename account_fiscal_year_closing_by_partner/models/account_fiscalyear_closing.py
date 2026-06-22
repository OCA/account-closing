from odoo import fields, models


class AccountFiscalyearClosing(models.Model):
    _inherit = "account.fiscalyear.closing"

    split_by_partner = fields.Boolean(
        string="Split closing by partner",
        default=True,
    )

    def button_calculate(self):
        res = super().button_calculate()
        for fyc in self.filtered(
            lambda f: f.split_by_partner and f.state == "calculated"
        ):
            configs = fyc.move_config_ids.filtered("move_id")
            # Closing configs (with mappings) must be split before opening
            # configs (with inverse), because the opening split mirrors the
            # closing move's per-partner lines.
            for config in configs.filtered("mapping_ids"):
                config._split_closing_lines_by_partner()
            for config in configs.filtered(lambda c: not c.mapping_ids and c.inverse):
                config._split_closing_lines_by_partner()
        return res

    def button_post(self):
        res = super().button_post()
        for fyc in self.filtered("split_by_partner"):
            fyc._reconcile_closing_lines()
        return res

    def _reconcile_closing_lines(self):
        self.ensure_one()
        buckets = {}
        for line in self.move_ids.line_ids:
            if not line.partner_id or not line.account_id.reconcile:
                continue
            if line.reconciled:
                continue
            key = (line.account_id.id, line.partner_id.id)
            buckets.setdefault(key, self.env["account.move.line"])
            buckets[key] |= line
        for lines in buckets.values():
            if len(lines) > 1:
                lines.reconcile()
