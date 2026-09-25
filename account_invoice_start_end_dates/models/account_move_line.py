# Copyright 2013-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import format_date


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    start_date = fields.Date(
        "Line Start Date",
        index=True,
        compute="_compute_start_end_dates",
        store=True,
        readonly=False,
        precompute=True,
    )
    end_date = fields.Date(
        "Line End Date",
        index=True,
        compute="_compute_start_end_dates",
        store=True,
        readonly=False,
        precompute=True,
    )
    must_have_dates = fields.Boolean(related="product_id.must_have_dates")

    @api.depends("move_id.invoice_date", "display_type")
    def _compute_start_end_dates(self):
        # The invoice date is only a default: we never overwrite dates that are
        # already set on the line, so that the user can enter another period.
        # The company options are deliberately not dependencies, otherwise
        # enabling them would fill the lines of all the existing invoices.
        for line in self:
            move = line.move_id
            company = move.company_id
            use_invoice_date = (
                move.is_purchase_document(include_receipts=True)
                and company.start_end_dates_from_bill_date
            ) or (
                move.is_sale_document(include_receipts=True)
                and company.start_end_dates_from_invoice_date
            )
            if (
                use_invoice_date
                and line.display_type == "product"
                and not line.start_date
                and not line.end_date
                and move.invoice_date
            ):
                line.start_date = move.invoice_date
                line.end_date = move.invoice_date

    @api.constrains(
        "start_date", "end_date", "display_type", "product_id", "parent_state"
    )
    def _check_start_end_dates(self):
        for moveline in self:
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

            if moveline.parent_state == "posted":
                # We enforce the presence of both dates only when posting the
                # invoice, because the native mass edit writes one field at a time:
                # setting the start date on a selection of draft move lines would
                # otherwise always fail before their end date can be set.
                if moveline.start_date and not moveline.end_date:
                    raise ValidationError(
                        _("Missing End Date for line '%s'.") % (moveline.display_name)
                    )
                if moveline.end_date and not moveline.start_date:
                    raise ValidationError(
                        _("Missing Start Date for line '%s'.") % (moveline.display_name)
                    )

                # We enforce start_end+end_date when product_id.must_have_dates=True
                # only when posting the invoice, because some users want to use the
                # module account_invoice_start_end_dates WITHOUT the module
                # sale_start_end_dates for a good reason.
                if (
                    moveline.display_type == "product"
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
