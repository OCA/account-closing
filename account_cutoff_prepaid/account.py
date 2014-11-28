# -*- encoding: utf-8 -*-
##############################################################################
#
#    Account Cut-off Prepaid module for OpenERP
#    Copyright (C) 2013 Akretion (http://www.akretion.com)
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


from openerp.osv import orm, fields
from openerp.tools.translate import _


class account_invoice_line(orm.Model):
    _inherit = 'account.invoice.line'

    _columns = {
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
    }

    def _check_start_end_dates(self, cr, uid, ids):
        for invline in self.browse(cr, uid, ids):
            if invline.start_date and not invline.end_date:
                raise orm.except_orm(
                    _('Error:'),
                    _("Missing End Date for invoice line with "
                        "Description '%s'.")
                    % (invline.name))
            if invline.end_date and not invline.start_date:
                raise orm.except_orm(
                    _('Error:'),
                    _("Missing Start Date for invoice line with "
                        "Description '%s'.")
                    % (invline.name))
            if invline.end_date and invline.start_date and \
                    invline.start_date > invline.end_date:
                raise orm.except_orm(
                    _('Error:'),
                    _("Start Date should be before or be the same as "
                        "End Date for invoice line with Description '%s'.")
                    % (invline.name))
            # Note : we can't check invline.product_id.must_have_dates
            # have start_date and end_date here, because it would
            # block automatic invoice generation. So we do the check
            # upon validation of the invoice (see below the function
            # action_move_create)
        return True

    _constraints = [
        (_check_start_end_dates, "Error msg in raise",
            ['start_date', 'end_date', 'product_id']),
    ]

    def move_line_get_item(self, cr, uid, line, context=None):
        res = super(account_invoice_line, self).move_line_get_item(
            cr, uid, line, context=context)
        res['start_date'] = line.start_date
        res['end_date'] = line.end_date
        return res


class account_move_line(orm.Model):
    _inherit = "account.move.line"

    _columns = {
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
    }

    def _check_start_end_dates(self, cr, uid, ids):
        for moveline in self.browse(cr, uid, ids):
            if moveline.start_date and not moveline.end_date:
                raise orm.except_orm(
                    _('Error:'),
                    _("Missing End Date for move line with Name '%s'.")
                    % (moveline.name))
            if moveline.end_date and not moveline.start_date:
                raise orm.except_orm(
                    _('Error:'),
                    _("Missing Start Date for move line with Name '%s'.")
                    % (moveline.name))
            if moveline.end_date and moveline.start_date and \
                    moveline.start_date > moveline.end_date:
                raise orm.except_orm(
                    _('Error:'),
                    _("Start Date should be before End Date for move line "
                        "with Name '%s'.")
                    % (moveline.name))
        # should we check that it's related to an expense / revenue ?
        # -> I don't think so
        return True

    _constraints = [(
        _check_start_end_dates,
        "Error msg in raise",
        ['start_date', 'end_date']
    )]


class account_invoice(orm.Model):
    _inherit = 'account.invoice'

    def inv_line_characteristic_hashcode(self, invoice, invoice_line):
        '''Add start and end dates to hashcode used when the option "Group
        Invoice Lines" is active on the Account Journal'''
        code = super(account_invoice, self).inv_line_characteristic_hashcode(
            invoice, invoice_line)
        hashcode = '%s-%s-%s' % (
            code, invoice_line.get('start_date', 'False'),
            invoice_line.get('end_date', 'False'),
        )
        return hashcode

    def line_get_convert(self, cr, uid, x, part, date, context=None):
        res = super(account_invoice, self).line_get_convert(
            cr, uid, x, part, date, context=context)
        res['start_date'] = x.get('start_date', False)
        res['end_date'] = x.get('end_date', False)
        return res

    def action_move_create(self, cr, uid, ids, context=None):
        '''Check that products with must_have_dates=True have
        Start and End Dates'''
        for invoice in self.browse(cr, uid, ids, context=context):
            for invline in invoice.invoice_line:
                if invline.product_id and invline.product_id.must_have_dates:
                    if not invline.start_date or not invline.end_date:
                        raise orm.except_orm(
                            _('Error:'),
                            _("Missing Start Date and End Date for invoice "
                                "line with Product '%s' which has the "
                                "property 'Must Have Start and End Dates'.")
                            % (invline.product_id.name))
        return super(account_invoice, self).action_move_create(
            cr, uid, ids, context=context)
