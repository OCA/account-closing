# -*- coding: utf-8 -*-
# © 2013-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, fields, api, _
from openerp.tools import float_is_zero
from openerp.exceptions import Warning as UserError


class AccountCutoff(models.Model):
    _inherit = 'account.cutoff'

    @api.model
    def _prepare_lines_from_move_lines(
            self, cutoff, stock_move, account_mapping):
        ato = self.env['account.tax']
        dpo = self.env['decimal.precision']
        assert cutoff.type in ('accrued_expense', 'accrued_revenue'),\
            "The field 'type' has a wrong value"
        qty_prec = dpo.precision_get('Product Unit of Measure')
        acc_prec = dpo.precision_get('Account')
        qty = stock_move.product_qty
        product = stock_move.product_id
        if float_is_zero(qty, precision_digits=qty_prec):
            return False
        if stock_move.invoice_line_ids:
            # In real life, all move lines related to an 1 invoice line
            # should be in the same state and have the same date
            inv_line = stock_move.invoice_line_ids[0]
            inv = inv_line.invoice_id
            if (
                    inv.state not in ('open', 'paid') and
                    inv.date_invoice <= cutoff.cutoff_date):
                return False
            account = inv_line.account_id
            currency = inv.currency_id
            analytic_account_id = inv_line.account_analytic_id.id or False
            price_unit = inv_line.price_unit * \
                (1 - (inv_line.discount or 0.0) / 100.0)
            uom = inv_line.uos_id
            taxes = inv_line.invoice_line_tax_id
            partner = inv.commercial_partner_id
            price_source = 'invoice'
        elif cutoff.type == 'accrued_expense':
            pur_line = stock_move.purchase_line_id
            if not pur_line:
                return False
            purchase = pur_line.order_id
            account = product.property_account_expense
            if not account:
                account = product.categ_id.property_account_expense_categ
            if not account:
                raise UserError(_(
                    "Missing expense account on product '%s' or on its "
                    "related product category '%s' (Picking '%s').") % (
                        product.name_get()[0][1],
                        product.categ_id.complete_name,
                        stock_move.picking_id.name))
            account = purchase.fiscal_position.map_account(account)
            currency = purchase.currency_id
            analytic_account_id = pur_line.account_analytic_id.id or False
            price_unit = pur_line.price_unit
            uom = pur_line.product_uom
            taxes = pur_line.taxes_id
            partner = purchase.partner_id.commercial_partner_id
            price_source = 'purchase'
        elif cutoff.type == 'accrued_revenue':
            so_line = stock_move.procurement_id.sale_line_id
            if not so_line:
                return False
            so = so_line.order_id
            account = product.property_account_income
            if not account:
                account = product.categ_id.property_account_income_categ
            if not account:
                raise UserError(_(
                    "Missing income account on product '%s' or on its "
                    "related product category '%s' (Picking '%s').") % (
                        product.name_get()[0][1],
                        product.categ_id.complete_name,
                        stock_move.picking_id.name))
            account = so.fiscal_position.map_account(account)
            currency = so.currency_id
            analytic_account_id = so.project_id.id or False
            price_unit = so_line.price_unit *\
                (1 - (so_line.discount or 0.0) / 100.0)
            uom = so_line.product_uom
            taxes = so_line.tax_id
            partner = so.partner_id.commercial_partner_id
            price_source = 'sale'

        company_currency = cutoff.company_currency_id
        # update price_unit to be in product uom
        price_unit = self.env['product.uom']._compute_qty_obj(
            uom, price_unit, stock_move.product_id.uom_id)
        sign = cutoff.type == 'accrued_expense' and -1 or 1
        tax_line_ids = []
        tax_res = taxes.compute_all(
            price_unit, qty, product=stock_move.product_id, partner=partner)
        amount = tax_res['total'] * sign  # =total without taxes
        price_unit_without_tax = amount / qty
        for tax_line in tax_res['taxes']:
            tax = ato.browse(tax_line['id'])
            if float_is_zero(tax_line['amount'], precision_digits=acc_prec):
                continue
            if cutoff.type == 'accrued_expense':
                tax_accrual_account_id = tax.account_accrued_expense_id.id
                tax_account_field_label = 'Accrued Expense Tax Account'
            elif cutoff.type == 'accrued_revenue':
                tax_accrual_account_id = tax.account_accrued_revenue_id.id
                tax_account_field_label = 'Accrued Revenue Tax Account'
            if not tax_accrual_account_id:
                raise UserError(_(
                    "Missing '%s' on tax '%s' "
                    "(Picking '%s', product '%s').") % (
                        tax_account_field_label,
                        tax.name,
                        stock_move.picking_id.name,
                        product.name_get()[0][1]))
            tax_amount = tax_line['amount'] * sign
            tax_accrual_amount = currency.with_context(
                date=cutoff.cutoff_date).compute(
                    tax_amount, company_currency)
            tax_line_ids.append((0, 0, {
                'tax_id': tax_line['id'],
                'base': currency.round(
                    tax_line['price_unit'] * qty),
                'amount': tax_amount,
                'sequence': tax_line['sequence'],
                'cutoff_account_id': tax_accrual_account_id,
                'cutoff_amount': tax_accrual_amount,
                'analytic_account_id':
                tax_line['account_analytic_collected_id'],
                # account_analytic_collected_id is for
                # invoices IN and OUT
                }))
        amount_company_currency = currency.with_context(
            date=cutoff.cutoff_date).compute(
                amount, company_currency)

        # we use account mapping here
        if account.id in account_mapping:
            accrual_account_id = account_mapping[account.id]
        else:
            accrual_account_id = account.id
        res = {
            'parent_id': cutoff.id,
            'stock_move_id': stock_move.id,
            'partner_id': partner.id,
            'name': stock_move.name,
            'account_id': account.id,
            'cutoff_account_id': accrual_account_id,
            'analytic_account_id': analytic_account_id,
            'currency_id': currency.id,
            'quantity': qty,
            'price_unit': price_unit_without_tax,
            'tax_ids': [(6, 0, taxes.ids)],
            'amount': amount,
            'cutoff_amount': amount_company_currency,
            'tax_line_ids': tax_line_ids,
            'price_source': price_source,
            }
        return res

    @api.multi
    def generate_accrual_lines(self):
        res = super(AccountCutoff, self).generate_accrual_lines()
        spo = self.env['stock.picking']
        aclo = self.env['account.cutoff.line']
        acmo = self.env['account.cutoff.mapping']

        pick_type_map = {
            'accrued_revenue': 'outgoing',
            'accrued_expense': 'incoming',
        }
        assert self.type in pick_type_map, \
            "self.type should be in pick_type_map.keys()"
        pickings = spo.search([
            ('picking_type_code', '=', pick_type_map[self.type]),
            ('state', '=', 'done'),
            ('date_done', '<=', self.cutoff_date),
            ('invoice_state', 'in', ('2binvoiced', 'invoiced')),
            '|',
            # when invoice_state = 2binvoiced
            # and invoice_state = invoiced / draft
            ('max_date_invoice', '=', False),
            ('max_date_invoice', '>', self.cutoff_date)
            ])

        # print "pick_ids=", pickings
        # Create account mapping dict
        account_mapping = acmo._get_mapping_dict(
            self.company_id.id, self.type)
        for picking in pickings:
            for move_line in picking.move_lines:
                vals = self._prepare_lines_from_move_lines(
                    self, move_line, account_mapping)
                if vals:
                    aclo.create(vals)
        return res


class AccountCutoffLine(models.Model):
    _inherit = 'account.cutoff.line'

    stock_move_id = fields.Many2one(
        'stock.move', string='Stock Move', readonly=True)
    picking_id = fields.Many2one(
        related='stock_move_id.picking_id', string='Picking',
        readonly=True, store=True)
    stock_move_date = fields.Datetime(
        related='stock_move_id.date', string='Transfer Date', readonly=True,
        store=True)
