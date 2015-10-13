# -*- encoding: utf-8 -*-
##############################################################################
#
#    Account Cut-off Accrual Picking module for OpenERP
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


class account_cutoff(orm.Model):
    _inherit = 'account.cutoff'

    def _prepare_lines_from_picking(
            self, cr, uid, ids, cur_cutoff, move_line, account_mapping,
            context=None):
        tax_obj = self.pool['account.tax']
        curr_obj = self.pool['res.currency']
        company_currency_id = cur_cutoff['company_currency_id'][0]
        assert cur_cutoff['type'] in ('accrued_expense', 'accrued_revenue'),\
            "The field 'type' has a wrong value"
        if cur_cutoff['type'] == 'accrued_expense':
            account_id = move_line.product_id.property_account_expense.id
            if not account_id:
                account_id = move_line.product_id.categ_id.\
                    property_account_expense_categ.id
            if not account_id:
                raise orm.except_orm(
                    _('Error:'),
                    _("Missing expense account on product '%s' or on its "
                        "related product category.")
                    % (move_line.product_id.name))
            currency = move_line.purchase_line_id.order_id.\
                pricelist_id.currency_id
            analytic_account_id = move_line.purchase_line_id.\
                account_analytic_id.id or False
            price_unit = move_line.purchase_line_id.price_unit
            taxes = move_line.purchase_line_id.taxes_id
            partner_id = move_line.purchase_line_id.order_id.partner_id.id
            tax_account_field_name = 'account_accrued_expense_id'
            tax_account_field_label = 'Accrued Expense Tax Account'

        elif cur_cutoff['type'] == 'accrued_revenue':
            account_id = move_line.product_id.property_account_income.id
            if not account_id:
                account_id = move_line.product_id.categ_id.\
                    property_account_income_categ.id
            if not account_id:
                raise orm.except_orm(
                    _('Error:'),
                    _("Missing income account on product '%s' or on its "
                        "related product category.")
                    % (move_line.product_id.name))
            currency = move_line.sale_line_id.order_id.pricelist_id.currency_id
            analytic_account_id = move_line.sale_line_id.order_id.\
                project_id.id or False
            discount = move_line.sale_line_id.discount
            price_unit = move_line.sale_line_id.price_unit *\
                (1 - (discount or 0.0) / 100.0)
            taxes = move_line.sale_line_id.tax_id
            partner_id = move_line.sale_line_id.order_id.partner_id.id
            tax_account_field_name = 'account_accrued_revenue_id'
            tax_account_field_label = 'Accrued Revenue Tax Account'

        currency_id = currency.id
        quantity = move_line.product_qty
        tax_line_ids = []
        tax_res = self.pool['account.tax'].compute_all(
            cr, uid, taxes, price_unit, quantity,
            move_line.product_id.id, partner_id)
        amount = tax_res['total']  # =total without taxes
        if cur_cutoff['type'] == 'accrued_expense':
            amount = amount * -1
        context_currency_compute = context.copy()
        context_currency_compute['date'] = cur_cutoff['cutoff_date']
        for tax_line in tax_res['taxes']:
            tax_read = tax_obj.read(
                cr, uid, tax_line['id'],
                [tax_account_field_name, 'name'], context=context)
            tax_accrual_account_id = tax_read[tax_account_field_name]
            if not tax_accrual_account_id:
                raise orm.except_orm(
                    _('Error:'),
                    _("Missing '%s' on tax '%s'.")
                    % (tax_account_field_label, tax_read['name']))
            else:
                tax_accrual_account_id = tax_accrual_account_id[0]
            if cur_cutoff['type'] == 'accrued_expense':
                tax_line['amount'] = tax_line['amount'] * -1
            if company_currency_id != currency_id:
                tax_accrual_amount = curr_obj.compute(
                    cr, uid, currency_id, company_currency_id,
                    tax_line['amount'],
                    context=context_currency_compute)
            else:
                tax_accrual_amount = tax_line['amount']
            tax_line_ids.append((0, 0, {
                'tax_id': tax_line['id'],
                'base': curr_obj.round(
                    cr, uid, currency,
                    tax_line['price_unit'] * quantity),
                'amount': tax_line['amount'],
                'sequence': tax_line['sequence'],
                'cutoff_account_id': tax_accrual_account_id,
                'cutoff_amount': tax_accrual_amount,
                'analytic_account_id':
                tax_line['account_analytic_collected_id'],
                # account_analytic_collected_id is for
                # invoices IN and OUT
            }))
        if company_currency_id != currency_id:
            amount_company_currency = curr_obj.compute(
                cr, uid, currency_id, company_currency_id, amount,
                context=context_currency_compute)
        else:
            amount_company_currency = amount

        # we use account mapping here
        if account_id in account_mapping:
            accrual_account_id = account_mapping[account_id]
        else:
            accrual_account_id = account_id
        res = {
            'parent_id': ids[0],
            'partner_id': partner_id,
            'stock_move_id': move_line.id,
            'name': move_line.name,
            'account_id': account_id,
            'cutoff_account_id': accrual_account_id,
            'analytic_account_id': analytic_account_id,
            'currency_id': currency_id,
            'quantity': quantity,
            'price_unit': price_unit,
            'tax_ids': [(6, 0, [tax.id for tax in taxes])],
            'amount': amount,
            'cutoff_amount': amount_company_currency,
            'tax_line_ids': tax_line_ids,
        }
        return res

    def get_lines_from_picking(self, cr, uid, ids, context=None):
        assert len(ids) == 1, \
            'This function should only be used for a single id at a time'
        pick_obj = self.pool['stock.picking']
        line_obj = self.pool['account.cutoff.line']
        mapping_obj = self.pool['account.cutoff.mapping']

        cur_cutoff = self.read(cr, uid, ids[0], [
            'line_ids', 'type', 'cutoff_date', 'company_id',
            'company_currency_id',
        ],
            context=context)
        # delete existing lines based on pickings
        to_delete_line_ids = line_obj.search(
            cr, uid, [
                ('parent_id', '=', cur_cutoff['id']),
                ('stock_move_id', '!=', False)
            ],
            context=context)
        if to_delete_line_ids:
            line_obj.unlink(cr, uid, to_delete_line_ids, context=context)
        pick_type_map = {
            'accrued_revenue': 'out',
            'accrued_expense': 'in',
        }
        assert cur_cutoff['type'] in pick_type_map, \
            "cur_cutoff['type'] should be in pick_type_map.keys()"
        pick_ids = pick_obj.search(cr, uid, [
            ('type', '=', pick_type_map[cur_cutoff['type']]),
            ('state', '=', 'done'),
            ('invoice_state', '=', '2binvoiced'),
            ('date_done', '<=', cur_cutoff['cutoff_date'])
        ], context=context)
        # print "pick_ids=", pick_ids
        # Create account mapping dict
        account_mapping = mapping_obj._get_mapping_dict(
            cr, uid, cur_cutoff['company_id'][0], cur_cutoff['type'],
            context=context)
        for picking in pick_obj.browse(cr, uid, pick_ids, context=context):
            for move_line in picking.move_lines:
                line_obj.create(
                    cr, uid, self._prepare_lines_from_picking(
                        cr, uid, ids, cur_cutoff, move_line,
                        account_mapping, context=context),
                    context=context)
        return True


class account_cutoff_line(orm.Model):
    _inherit = 'account.cutoff.line'

    _columns = {
        'stock_move_id': fields.many2one(
            'stock.move', 'Stock Move', readonly=True),
        'product_id': fields.related(
            'stock_move_id', 'product_id', type='many2one',
            relation='product.product', string='Product', readonly=True),
        'picking_id': fields.related(
            'stock_move_id', 'picking_id', type='many2one',
            relation='stock.picking', string='Picking', readonly=True),
        'picking_date_done': fields.related(
            'picking_id', 'date_done', type='date',
            string='Date Done of the Picking', readonly=True),
    }
