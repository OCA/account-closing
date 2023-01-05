# Copyright 2013-2019 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class AccountCutoff(models.Model):
    _inherit = 'account.cutoff'

    def picking_prepare_cutoff_line(self, vdict, account_mapping):
        ato = self.env['account.tax']
        dpo = self.env['decimal.precision']
        assert self.cutoff_type in ('accrued_expense', 'accrued_revenue'),\
            "The field 'cutoff_type' has a wrong value"
        qty_prec = dpo.precision_get('Product Unit of Measure')
        cur_rprec = vdict['currency'].rounding
        qty = vdict['precut_delivered_qty'] - vdict['precut_invoiced_qty']
        if float_is_zero(qty, precision_digits=qty_prec):
            return False

        company_currency = self.company_currency_id
        currency = vdict['currency']
        sign = self.cutoff_type == 'accrued_expense' and -1 or 1
        amount = qty * vdict['price_unit'] * sign
        amount_company_currency = vdict['currency'].with_context(
            date=self.cutoff_date).compute(amount, company_currency)

        tax_line_ids = []
        tax_res = vdict['taxes'].compute_all(
            vdict['price_unit'], currency=currency, quantity=qty,
            product=vdict['product'], partner=vdict['partner'])
        for tax_line in tax_res['taxes']:
            tax = ato.browse(tax_line['id'])
            if float_is_zero(tax_line['amount'], precision_rounding=cur_rprec):
                continue
            if self.cutoff_type == 'accrued_expense':
                tax_accrual_account_id = tax.account_accrued_expense_id.id
                tax_account_field_label = _('Accrued Expense Tax Account')
            elif self.cutoff_type == 'accrued_revenue':
                tax_accrual_account_id = tax.account_accrued_revenue_id.id
                tax_account_field_label = _('Accrued Revenue Tax Account')
            if not tax_accrual_account_id:
                raise UserError(_(
                    "Missing '%s' on tax '%s'.") % (
                        tax_account_field_label, tax.display_name))
            tax_amount = tax_line['amount'] * sign
            tax_accrual_amount = currency.with_context(
                date=self.cutoff_date).compute(tax_amount, company_currency)
            tax_line_ids.append((0, 0, {
                'tax_id': tax_line['id'],
                'base': tax_line['base'],
                'amount': tax_amount,
                'sequence': tax_line['sequence'],
                'cutoff_account_id': tax_accrual_account_id,
                'cutoff_amount': tax_accrual_amount,
                }))

        # Use account mapping
        account_id = vdict['account_id']
        if account_id in account_mapping:
            accrual_account_id = account_mapping[account_id]
        else:
            accrual_account_id = account_id
        vals = {
            'parent_id': self.id,
            'partner_id': vdict['partner'].id,
            'name': vdict['name'],
            'account_id': account_id,
            'cutoff_account_id': accrual_account_id,
            'analytic_account_id': vdict['analytic_account_id'],
            'currency_id': vdict['currency'].id,
            'quantity': qty,
            'price_unit': vdict['price_unit'],
            'tax_ids': [(6, 0, vdict['taxes'].ids)],
            'amount': amount,
            'cutoff_amount': amount_company_currency,
            'tax_line_ids': tax_line_ids,
            'price_origin': vdict.get('price_origin'),
            }
        return vals

    def _picking_done_min_date(self):
        self.ensure_one()
        cutoff_date_dt = self.cutoff_date
        min_date_dt = cutoff_date_dt - relativedelta(months=3)
        min_date = fields.Date.to_string(min_date_dt)
        return min_date

    def order_line_update_oline_dict(self, order_line, order_type, oline_dict):
        assert order_line not in oline_dict
        dpo = self.env['decimal.precision']
        qty_prec = dpo.precision_get('Product Unit of Measure')
        # These fields have the same name on PO and SO
        order = order_line.order_id
        product = order_line.product_id
        product_uom = product.uom_id
        oline_dict[order_line] = {
            'precut_delivered_qty': 0.0,  # in product_uom
            'precut_invoiced_qty': 0.0,  # in product_uom
            'name': _('%s line ID %d: %s') % (
                order.name, order_line.id, order_line.name),
            'product': product,
            'partner': order.partner_id.commercial_partner_id,
            }
        if order_type == 'purchase':
            moves = order_line.move_ids
            ilines = order_line.invoice_lines
            invoice_type = 'in_invoice'
        elif order_type == 'sale':
            moves = order_line.move_ids
            ilines = self.env['account.invoice.line'].search([
                ('sale_line_ids', 'in', order_line.id)])
            invoice_type = 'out_invoice'
        for move in moves:
            # TODO: improve comparaison of date and datetime
            # for our friends far away from GMT
            if move.state == 'done' and move.date.date() <= self.cutoff_date:
                move_qty = move.product_uom._compute_quantity(
                    move.product_uom_qty, product_uom)
                oline_dict[order_line]['precut_delivered_qty'] += move_qty
        price_origin = False
        for iline in ilines:
            invoice = iline.invoice_id
            if (
                    invoice.state in ('open', 'in_payment', 'paid') and
                    invoice.type == invoice_type and
                    float_compare(
                        iline.quantity, 0, precision_digits=qty_prec) > 0):
                iline_qty_puom = iline.uom_id._compute_quantity(
                    iline.quantity, product_uom)
                if invoice.date_invoice <= self.cutoff_date:
                    oline_dict[order_line][
                        'precut_invoiced_qty'] += iline_qty_puom
                # Most recent invoice line used for price_unit, account,...
                price_unit = iline.price_subtotal / iline_qty_puom
                price_origin = _('Invoice %s line ID %d') % (
                    invoice.number, iline.id)
                currency = invoice.currency_id
                account_id = iline.account_id.id
                analytic_account_id = iline.account_analytic_id.id
                taxes = iline.invoice_line_tax_ids
        if not price_origin:
            if order_type == 'purchase':
                oline_qty_puom = order_line.product_uom._compute_quantity(
                    order_line.product_qty, product_uom)
                price_unit = order_line.price_subtotal / oline_qty_puom
                price_origin = _('%s line ID %d') % (order.name, order_line.id)
                currency = order.currency_id
                analytic_account_id = order_line.account_analytic_id.id
                taxes = order_line.taxes_id
                account = product.product_tmpl_id.\
                    _get_product_accounts()['expense']
                if not account:
                    raise UserError(_(
                        "Missing expense account on product '%s' or on its "
                        "related product category '%s'.") % (
                            product.display_name,
                            product.categ_id.display_name))
                account_id = order.fiscal_position_id.map_account(account).id
            elif order_type == 'sale':
                oline_qty_puom = order_line.product_uom._compute_quantity(
                    order_line.product_uom_qty, product_uom)
                price_unit = order_line.price_subtotal / oline_qty_puom
                price_origin = '%s line ID %d' % (order.name, order_line.id)
                currency = order.currency_id
                analytic_account_id = order.analytic_account_id.id
                taxes = order_line.tax_id
                account = product.product_tmpl_id.\
                    _get_product_accounts()['income']
                if not account:
                    raise UserError(_(
                        "Missing income account on product '%s' or on its "
                        "related product category '%s'.") % (
                            product.display_name,
                            product.categ_id.display_name))
                account_id = order.fiscal_position_id.map_account(account).id

        oline_dict[order_line].update({
            'price_unit': price_unit,
            'price_origin': price_origin,
            'currency': currency,
            'analytic_account_id': analytic_account_id,
            'account_id': account_id,
            'taxes': taxes,
            })

    def stock_move_update_oline_dict(self, move_line, oline_dict):
        dpo = self.env['decimal.precision']
        qty_prec = dpo.precision_get('Product Unit of Measure')
        if self.cutoff_type == 'accrued_expense':
            if (
                    move_line.purchase_line_id and
                    move_line.purchase_line_id not in oline_dict and
                    not float_is_zero(
                        move_line.purchase_line_id.product_qty,
                        precision_digits=qty_prec)):
                self.order_line_update_oline_dict(
                    move_line.purchase_line_id, 'purchase', oline_dict)
        elif self.cutoff_type == 'accrued_revenue':
            if (
                    move_line.sale_line_id and
                    move_line.sale_line_id not in oline_dict and
                    not float_is_zero(
                        move_line.sale_line_id.product_uom_qty,
                        precision_digits=qty_prec)):
                self.order_line_update_oline_dict(
                    move_line.sale_line_id, 'sale', oline_dict)

    def get_lines(self):
        res = super(AccountCutoff, self).get_lines()
        spo = self.env['stock.picking']
        aclo = self.env['account.cutoff.line']
        acmo = self.env['account.cutoff.mapping']

        pick_type_map = {
            'accrued_revenue': 'outgoing',
            'accrued_expense': 'incoming',
            }
        cutoff_type = self.cutoff_type
        if cutoff_type not in pick_type_map:
            return res

        # Create account mapping dict
        account_mapping = acmo._get_mapping_dict(
            self.company_id.id, cutoff_type)

        # TODO date_done is a Datetime field, so maybe we need more clever code
        # for our friends which are far away from GMT
        pickings = spo.search([
            ('picking_type_code', '=', pick_type_map[cutoff_type]),
            ('state', '=', 'done'),
            ('date_done', '<=', self.cutoff_date),
            ('date_done', '>=', self._picking_done_min_date()),
            ])

        oline_dict = {}  # order line dict
        # key = PO line or SO line recordset
        # value = {
        #   'precut_delivered_qty': 1.0,
        #   'precut_invoiced_qty': 0.0,
        #   'price_unit': 12.42,
        #   }
        # -> we use precut_delivered_qty - precut_invoiced_qty
        for p in pickings:
            for move in p.move_lines.filtered(lambda m: m.state == 'done'):
                self.stock_move_update_oline_dict(move, oline_dict)

        # from pprint import pprint
        # pprint(oline_dict)
        for vdict in oline_dict.values():
            vals = self.picking_prepare_cutoff_line(vdict, account_mapping)
            if vals:
                aclo.create(vals)
        return res
