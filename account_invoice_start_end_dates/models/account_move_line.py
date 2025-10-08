# Copyright 2013-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import format_date


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    start_date = fields.Date(index=True)
    end_date = fields.Date(index=True)
    must_have_dates = fields.Boolean(related="product_id.must_have_dates")

    @api.constrains(
        "start_date", "end_date", "display_type", "product_id", "parent_state"
    )
    def _check_start_end_dates(self):
        for moveline in self:
            if moveline.start_date and not moveline.end_date:
                raise ValidationError(
                    _("Missing End Date for line '%s'.") % (moveline.display_name)
                )
            if moveline.end_date and not moveline.start_date:
                raise ValidationError(
                    _("Missing Start Date for line '%s'.") % (moveline.display_name)
                )
            if (
                moveline.end_date
                and moveline.start_date
                and moveline.start_date > moveline.end_date
            ):
                raise ValidationError(
                    _(
                        "Start Date (%(start_date)s) should be before End Date "
                        "(%(end_date)s) for line '%(name)s'."
                    )
                    % {
                        "start_date": format_date(self.env, moveline.start_date),
                        "end_date": format_date(self.env, moveline.end_date),
                        "name": moveline.display_name,
                    }
                )
            # We enforce start_end+end_date when product_id.must_have_dates=True
            # only when posting the invoice, because some users want to use the
            # module account_invoice_start_end_dates WITHOUT the module
            # sale_start_end_dates for a good reason.
            if (
                moveline.parent_state == "posted"
                and moveline.display_type == "product"
                and moveline.product_id.must_have_dates
                and not moveline.start_date
            ):
                raise ValidationError(
                    _(
                        "Missing Start Date for invoice "
                        "line with Product '%s' which has the "
                        "property 'Must Have Start/End Dates'."
                    )
                    % (moveline.product_id.display_name)
                )
