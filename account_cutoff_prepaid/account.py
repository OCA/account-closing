# -*- coding: utf-8 -*-
##############################################################################
#
#    Account Cut-off Prepaid module for Odoo
#    Copyright (C) 2013-2015 Akretion (http://www.akretion.com)
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from openerp import models, fields, api, _
from openerp.exceptions import ValidationError
from openerp.exceptions import Warning as UserError


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')

    @api.multi
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
            # block automatic invoice generation. So we do the check
            # upon validation of the invoice (see below the function
            # action_move_create)

    @api.model
    def move_line_get_item(self, line):
        res = super(AccountInvoiceLine, self).move_line_get_item(
            line)
        res['start_date'] = line.start_date
        res['end_date'] = line.end_date
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')

    @api.multi
    @api.constrains('start_date', 'end_date')
    def _check_start_end_dates(self):
        for moveline in self:
            if moveline.start_date and not moveline.end_date:
                raise ValidationError(
                    _("Missing End Date for move line with Name '%s'.")
                    % (moveline.name))
            if moveline.end_date and not moveline.start_date:
                raise ValidationError(
                    _("Missing Start Date for move line with Name '%s'.")
                    % (moveline.name))
            if moveline.end_date and moveline.start_date and \
                    moveline.start_date > moveline.end_date:
                raise ValidationError(
                    _("Start Date should be before End Date for move line "
                        "with Name '%s'.")
                    % (moveline.name))
        # should we check that it's related to an expense / revenue ?
        # -> I don't think so


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def inv_line_characteristic_hashcode(self, invoice_line):
        '''Add start and end dates to hashcode used when the option "Group
        Invoice Lines" is active on the Account Journal'''
        code = super(AccountInvoice, self).inv_line_characteristic_hashcode(
            invoice_line)
        hashcode = '%s-%s-%s' % (
            code, invoice_line.get('start_date', 'False'),
            invoice_line.get('end_date', 'False'),
        )
        return hashcode

    @api.model
    def line_get_convert(self, line, part, date):
        res = super(AccountInvoice, self).line_get_convert(
            line, part, date)
        res['start_date'] = line.get('start_date', False)
        res['end_date'] = line.get('end_date', False)
        return res

    @api.multi
    def action_move_create(self):
        '''Check that products with must_have_dates=True have
        Start and End Dates'''
        for invoice in self:
            for invline in invoice.invoice_line:
                if invline.product_id and invline.product_id.must_have_dates:
                    if not invline.start_date or not invline.end_date:
                        raise UserError(
                            _("Missing Start Date and End Date for invoice "
                                "line with Product '%s' which has the "
                                "property 'Must Have Start and End Dates'.")
                            % (invline.product_id.name))
        return super(AccountInvoice, self).action_move_create()
