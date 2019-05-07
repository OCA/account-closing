# Copyright 2013-2016 Akretion, Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    start_date = fields.Date()
    end_date = fields.Date()
    must_have_dates = fields.Boolean(
        related='product_id.must_have_dates', readonly=True
    )

    @api.constrains('start_date', 'end_date')
    def _check_start_end_dates(self):
        for invline in self:
            if invline.start_date and not invline.end_date:
                raise ValidationError(
                    _("Missing End Date for invoice line with "
                        "Description '%s'.")
                    % (invline.name))
            if invline.end_date and not invline.start_date:
                raise ValidationError(
                    _("Missing Start Date for invoice line with "
                        "Description '%s'.")
                    % (invline.name))
            if invline.end_date and invline.start_date and \
                    invline.start_date > invline.end_date:
                raise ValidationError(
                    _("Start Date should be before or be the same as "
                        "End Date for invoice line with Description '%s'.")
                    % (invline.name))
            # Note : we can't check invline.product_id.must_have_dates
            # have start_date and end_date here, because it would
            # block automatic invoice generation/import. So we do the check
            # upon validation of the invoice (see below the function
            # action_move_create)


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def inv_line_characteristic_hashcode(self, invoice_line):
        """Add start and end dates to hashcode used when the option "Group
        Invoice Lines" is active on the Account Journal"""
        code = super().inv_line_characteristic_hashcode(
            invoice_line
        )
        hashcode = '%s-%s-%s' % (
            code,
            invoice_line.get('start_date', 'False'),
            invoice_line.get('end_date', 'False'),
        )
        return hashcode

    @api.model
    def line_get_convert(self, line, part):
        """Copy from invoice to move lines"""
        res = super().line_get_convert(line, part)
        res['start_date'] = line.get('start_date', False)
        res['end_date'] = line.get('end_date', False)
        return res

    @api.model
    def invoice_line_move_line_get(self):
        """Copy from invoice line to move lines"""
        res = super().invoice_line_move_line_get()
        ailo = self.env['account.invoice.line']
        for move_line_dict in res:
            iline = ailo.browse(move_line_dict['invl_id'])
            move_line_dict['start_date'] = iline.start_date
            move_line_dict['end_date'] = iline.end_date
        return res

    def action_move_create(self):
        """Check that products with must_have_dates=True have
        Start and End Dates"""
        for invoice in self:
            for iline in invoice.invoice_line_ids:
                if iline.product_id and iline.product_id.must_have_dates:
                    if not iline.start_date or not iline.end_date:
                        raise UserError(_(
                            "Missing Start Date and End Date for invoice "
                            "line with Product '%s' which has the "
                            "property 'Must Have Start and End Dates'.")
                            % (iline.product_id.name))
        return super().action_move_create()
