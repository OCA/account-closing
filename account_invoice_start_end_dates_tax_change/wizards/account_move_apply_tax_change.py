# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from dateutil.relativedelta import relativedelta

from odoo import fields, models


# NOTE: method copied from recent Odoo versions (odoo.tools.date_utils)
def date_subtract(value, *args, **kwargs):
    """
    Return the difference between ``value`` and a :class:`relativedelta`.

    :param value: initial date or datetime.
    :param args: positional args to pass directly to :class:`relativedelta`.
    :param kwargs: keyword args to pass directly to :class:`relativedelta`.
    :return: the resulting date/datetime.
    """
    return value - relativedelta(*args, **kwargs)


class AccountMoveApplyTaxChange(models.TransientModel):
    _inherit = "account.move.apply.tax.change"

    def _skip_line(self, line):
        if self._is_recurring_line(line):
            if self._is_recurring_tax_change_required(line):
                return False
            return True
        return super(AccountMoveApplyTaxChange, self)._skip_line(line)

    def _is_recurring_line(self, line):
        return line.start_date and line.end_date

    def _is_recurring_tax_change_required(self, line):
        # Start & end dates defined in the scope of the tax changes
        return line.start_date <= self.tax_change_id.date < line.end_date

    def _change_taxes(self, line):
        if self._is_recurring_line(line):
            if self._is_recurring_tax_change_required(line):
                # Split the invoice line by applying a prorata on the unit price
                # NOTE: if the tax change occurs on 2024-02-01, the end date
                # of the split invoice line will be the day before (2024-01-31)
                # such as it doesn't overlap with the start date of the new line.
                tax_change_date = fields.Date.from_string(self.tax_change_id.date)
                new_end_date = date_subtract(tax_change_date, days=1)
                # Dates subtractions are not inclusives so we add +1 day each time
                end_date = fields.Date.from_string(line.end_date)
                start_date = fields.Date.from_string(line.start_date)
                total_days = (end_date - start_date).days + 1
                days_until_change = (new_end_date - start_date).days + 1
                price_unit1 = line.price_unit * days_until_change / total_days
                price_unit2 = line.price_unit - price_unit1
                new_line_vals = self._prepare_new_line_values(line, price_unit2)
                line_vals = self._prepare_existing_line_values(line, price_unit1)
                new_line = line.create(new_line_vals)
                new_line = self._hook_new_line_before_change_taxes(new_line)
                # Update the taxes only on the new line
                res = super(AccountMoveApplyTaxChange, self)._change_taxes(new_line)
                new_line = self._hook_new_line_after_change_taxes(new_line)
                # Update the existing line that keep the current tax
                line.write(line_vals)
                lines = line | new_line
                lines.invalidate_cache()
                lines.modified(["start_date", "end_date", "price_unit"])
                lines.recompute()
                invoice = lines.mapped("invoice_id")
                invoice.compute_taxes()
                return res
            # Start & end dates defined but not in the scope of the tax changes
            return
        return super(AccountMoveApplyTaxChange, self)._change_taxes(line)

    def _prepare_new_line_values(self, existing_line, price_unit):
        return existing_line.copy_data(
            {
                "start_date": self.tax_change_id.date,
                "end_date": existing_line.end_date,
                "price_unit": price_unit,
            }
        )[0]

    def _prepare_existing_line_values(self, line, price_unit):
        return {
            "end_date": self.tax_change_id.date,
            "price_unit": price_unit,
        }

    def _hook_new_line_before_change_taxes(self, line):
        """Hook to override. Return the line record.

        Called once the new line is created but the new tax is still not applied.
        """
        return line

    def _hook_new_line_after_change_taxes(self, line):
        """Hook to override. Return the line record.

        Called once the new tax is applied on the new created line.
        """
        return line
