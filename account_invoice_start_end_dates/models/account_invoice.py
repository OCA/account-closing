# Copyright 2013-2016 Akretion, Alexis de Lattre <alexis.delattre@akretion.com>
# Copyright 2023 Simone Rubino - TAKOBI
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

    @api.model
    def _group_tax_move_lines_values_by_dates(self, tax_move_lines_values):
        """Group `tax_move_lines_values` by the start/end dates
        of the corresponding invoice lines.

        Tax lines are only grouped if their Tax has no Account
        because only in this case the generated move lines are costs.
        """
        tax_move_lines_values_by_dates = {}
        tax_line_model = self.env['account.invoice.tax']
        tax_model = self.env['account.tax']
        for tax_move_line_values in tax_move_lines_values:
            tax_id = tax_move_line_values['tax_line_id']
            tax = tax_model.browse(tax_id)
            if not tax.account_id:
                invoice_tax_line_id = tax_move_line_values['invoice_tax_line_id']
                invoice_tax_line = tax_line_model.browse(invoice_tax_line_id)
                all_invoice_lines = invoice_tax_line.invoice_id.invoice_line_ids
                tax_invoice_lines = all_invoice_lines.filtered(
                    lambda il:
                    tax in il.invoice_line_tax_ids
                    or tax in il.invoice_line_tax_ids.mapped('children_tax_ids')
                )
                for line in tax_invoice_lines:
                    start_date, end_date = line.start_date, line.end_date
                    tax_move_lines_values_by_dates \
                        .setdefault((start_date, end_date), []) \
                        .append(tax_move_line_values)
        return tax_move_lines_values_by_dates

    @api.model
    def tax_line_move_line_get(self):
        tax_move_lines_values = super().tax_line_move_line_get()
        tax_move_lines_values_by_dates = \
            self._group_tax_move_lines_values_by_dates(tax_move_lines_values)

        # Assign the start/end dates to each move line, creating more if needed
        for tax_move_line_values in tax_move_lines_values:
            start_end_dates = [
                start_end_date
                for start_end_date, values in tax_move_lines_values_by_dates.items()
                if tax_move_line_values in values
            ]
            if not start_end_dates:
                continue

            # The first dates couple updates the existing values
            start_date, end_date = start_end_dates[0]
            tax_move_line_values.update({
                'start_date': start_date,
                'end_date': end_date,
            })
            more_start_end_dates = start_end_dates[1:]
            if more_start_end_dates:
                # The remaining dates couples create copies
                # of the current move line with the given dates.
                # Price has to be equally distributed among
                # all the new and existing lines.
                tax_move_line_values['price'] /= len(start_end_dates)
                for start_date, end_date in more_start_end_dates:
                    new_move_line_values = tax_move_line_values.copy()
                    new_move_line_values.update({
                        'start_date': start_date,
                        'end_date': end_date,
                    })
                    tax_move_lines_values.append(new_move_line_values)

        return tax_move_lines_values

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
