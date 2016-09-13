# -*- coding: utf-8 -*-
# © 2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp.osv import orm, fields
from openerp.tools.translate import _


class account_cutoff(orm.Model):
    _inherit = 'account.cutoff'

    def _prepare_lines_from_invoice_lines(
            self, cr, uid, cur_cutoff, inv_line, account_mapping,
            context=None):
        tax_obj = self.pool['account.tax']
        curr_obj = self.pool['res.currency']
        inv = inv_line.invoice_id
        assert cur_cutoff.type in ('accrued_expense', 'accrued_revenue'),\
            "The field 'type' has a wrong value"
        if not inv_line.move_line_ids:
            return False
        # In real life, all move lines related to an 1 invoice line
        # should be in the same state and have the same date
        if any([move.state != 'done' for move in inv_line.move_line_ids]):
            return False
        if any([
                move.date > cur_cutoff.cutoff_date
                for move in inv_line.move_line_ids]):
            return False

        company_currency_id = cur_cutoff.company_currency_id.id
        currency = inv.currency_id
        currency_id = inv.currency_id.id
        quantity = inv_line.quantity
        tax_line_ids = []
        price = inv_line.price_unit * (1 - (inv_line.discount or 0.0) / 100.0)
        tax_res = self.pool['account.tax'].compute_all(
            cr, uid, inv_line.invoice_line_tax_id, price, inv_line.quantity,
            product=inv_line.product_id, partner=inv.partner_id)
        sign = cur_cutoff.type == 'accrued_expense' and -1 or 1
        amount = inv_line.price_subtotal * sign  # = tax_res['total'] * sign
        context_currency_compute = context.copy()
        context_currency_compute['date'] = cur_cutoff.cutoff_date
        for tax_line in tax_res['taxes']:
            tax = tax_obj.browse(
                cr, uid, tax_line['id'], context=context)

            if cur_cutoff.type == 'accrued_expense':
                tax_accrual_account_id = tax.account_accrued_expense_id.id
                tax_account_field_label = 'Accrued Expense Tax Account'
            elif cur_cutoff.type == 'accrued_revenue':
                tax_accrual_account_id = tax.account_accrued_revenue_id.id
                tax_account_field_label = 'Accrued Revenue Tax Account'
            if not tax_accrual_account_id:
                raise orm.except_orm(
                    _('Error:'),
                    _("Missing '%s' on tax '%s'.")
                    % (tax_account_field_label, tax.name))
            tax_amount = tax_line['amount'] * sign
            tax_accrual_amount = curr_obj.compute(
                cr, uid, currency_id, company_currency_id,
                tax_amount, context=context_currency_compute)
            tax_line_ids.append((0, 0, {
                'tax_id': tax_line['id'],
                'base': curr_obj.round(
                    cr, uid, currency,
                    tax_line['price_unit'] * quantity),
                'amount': tax_amount,
                'sequence': tax_line['sequence'],
                'cutoff_account_id': tax_accrual_account_id,
                'cutoff_amount': tax_accrual_amount,
                'analytic_account_id':
                tax_line['account_analytic_collected_id'],
                # account_analytic_collected_id is for
                # invoices IN and OUT
                }))
        amount_company_currency = curr_obj.compute(
            cr, uid, currency_id, company_currency_id, amount,
            context=context_currency_compute)

        # we use account mapping here
        account_id = inv_line.account_id.id
        if account_id in account_mapping:
            accrual_account_id = account_mapping[account_id]
        else:
            accrual_account_id = account_id
        res = {
            'parent_id': cur_cutoff.id,
            'invoice_line_id': inv_line.id,
            'partner_id': inv.commercial_partner_id.id,
            'name': inv_line.name,
            'account_id': account_id,
            'cutoff_account_id': accrual_account_id,
            'analytic_account_id': inv_line.account_analytic_id.id or False,
            'currency_id': inv.currency_id.id,
            'quantity': inv_line.quantity,
            'tax_ids': [(6, 0, inv_line.invoice_line_tax_id.ids or [])],
            'amount': amount,
            'cutoff_amount': amount_company_currency,
            'tax_line_ids': tax_line_ids,
            }
        return res

    def get_lines_from_invoices(self, cr, uid, ids, context=None):
        assert len(ids) == 1, \
            'This function should only be used for a single id at a time'
        aio = self.pool['account.invoice']
        line_obj = self.pool['account.cutoff.line']
        mapping_obj = self.pool['account.cutoff.mapping']

        cur_cutoff = self.browse(cr, uid, ids[0], context=context)
        # delete existing lines
        to_delete_line_ids = line_obj.search(
            cr, uid, [
                ('parent_id', '=', cur_cutoff.id),
                ('invoice_line_id', '!=', False)
                ],
            context=context)
        if to_delete_line_ids:
            line_obj.unlink(cr, uid, to_delete_line_ids, context=context)
        inv_type_map = {
            'accrued_revenue': 'out_invoice',
            'accrued_expense': 'in_invoice',
        }
        assert cur_cutoff.type in inv_type_map, \
            "cur_cutoff.type should be in pick_type_map.keys()"
        inv_ids = aio.search(cr, uid, [
            '|',
            ('date_invoice', '>', cur_cutoff.cutoff_date),
            ('date_invoice', '=', False),
            ('type', '=', inv_type_map[cur_cutoff.type]),
            ('state', '!=', 'cancel'),
            ('picking_ids', '!=', False),
            ], context=context)
        # print "inv_ids=", inv_ids
        # Create account mapping dict
        account_mapping = mapping_obj._get_mapping_dict(
            cr, uid, cur_cutoff.company_id.id, cur_cutoff.type,
            context=context)
        for inv in aio.browse(cr, uid, inv_ids, context=context):
            # all related pickings should be 'done'
            # if, for some strange reasons, it is not the case,
            # we just skip the invoice
            if any([pick.state != 'done' for pick in inv.picking_ids]):
                continue
            if any([
                    pick.date_done <= cur_cutoff.cutoff_date
                    for pick in inv.picking_ids]):
                for iline in inv.invoice_line:
                    vals = self._prepare_lines_from_invoice_lines(
                        cr, uid, cur_cutoff, iline,
                        account_mapping, context=context)
                    if vals:
                        line_obj.create(cr, uid, vals, context=context)
        return True


class account_cutoff_line(orm.Model):
    _inherit = 'account.cutoff.line'

    _columns = {
        'invoice_line_id': fields.many2one(
            'account.invoice.line', 'Invoice Line', readonly=True),
        'product_id': fields.related(
            'invoice_line_id', 'product_id', type='many2one',
            relation='product.product', string='Product', readonly=True),
        'stock_move_id': fields.related(
            'invoice_line_id', 'move_line_ids', type='many2one',
            relation='stock.move', string='Stock Move', readonly=True),
        'picking_id': fields.related(
            'invoice_line_id', 'move_line_ids', 'picking_id', type='many2one',
            relation='stock.picking', string='Picking', readonly=True),
        'stock_move_date_done': fields.related(
            'invoice_line_id', 'move_line_ids', 'date', type='date',
            string='Date Done of the Stock Move', readonly=True),
        }
