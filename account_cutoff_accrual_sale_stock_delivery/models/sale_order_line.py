# Copyright 2026 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _inherit = ["sale.order.line", "order.line.cutoff.accrual.mixin"]

    def _get_cutoff_accrual_delivered_min_date(self):
        self.ensure_one()
        if not self.is_delivery:
            return super()._get_cutoff_accrual_delivered_min_date()
        # For a delivery line, the invoicing date is the first delivery date of
        # any other invoiceable line
        order_lines = self.order_id.order_line.filtered(
            lambda line: not line.is_delivery
            and not line.is_downpayment
            and not line.display_type
        )
        dates = list(
            filter(
                None,
                (line._get_cutoff_accrual_delivered_min_date() for line in order_lines),
            )
        )
        if not dates:
            return
        date = min(dates)
        # In case the delivery line has been created later, it could not have
        # been invoiced before it's creation
        tz = self.order_id.company_id.partner_id.tz or "UTC"
        create_date = fields.Datetime.context_timestamp(
            self.with_context(tz=tz),
            self.create_date,
        ).date()
        return max(create_date, date)
