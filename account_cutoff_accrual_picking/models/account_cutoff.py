# -*- coding: utf-8 -*-
##############################################################################
#
#    Account Cut-off Accrual Picking module for OpenERP
#    Copyright (C) 2018 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
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

import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountCutoff(models.Model):
    _inherit = 'account.cutoff'

    @api.model
    def _inherit_default_cutoff_account_id(self):
        """ Set up default account for a new cutoff """
        account_id = super(AccountCutoff,
                           self)._inherit_default_cutoff_account_id()
        type_cutoff = self.env.context.get('type')
        company = self.env.user.company_id
        if type_cutoff == 'accrued_expense':
            account_id = company.default_accrued_expense_account_id.id or False
        elif type_cutoff == 'accrued_revenue':
            account_id = company.default_accrued_revenue_account_id.id or False
        return account_id

    def _get_account_mapping(self):
        """ Prepare account mapping """
        return self.env['account.cutoff.mapping']._get_mapping_dict(
            self.company_id.id, self.type)

    def _get_account(self, line, type, fpos):
        if type in 'accrued_revenue':
            map_type = 'income'
        else:
            map_type = 'expense'
        account = line.product_id.product_tmpl_id.get_product_accounts(
            fpos)[map_type]
        if not account:
            raise UserError(
                _("Error: Missing %s account on product '%s' or on "
                    "related product category.") % (
                        _(map_type), line.product_id.name))
        return account

    def _prepare_line(self, line):
        """
        Calculate accrued expense using purchase.order.line
        or accrued revenu using sale.order.line
        """
        assert self.type in ('accrued_expense', 'accrued_revenue'),\
            "The field 'type' has a wrong value"

        partner = line.order_id.partner_id
        fpos = partner.property_account_position_id
        account_id = self._get_account(line, self.type, fpos).id
        accrual_account_id = self._get_account_mapping().get(
            account_id, account_id)

        received_qty = line.qty_received

        if self.type == 'accrued_expense':
            # Processing purchase order line
            analytic_account_id = line.account_analytic_id.id
            price_unit = line.price_unit
            taxes = line.taxes_id
            taxes = fpos.map_tax(taxes)
            # The quantity received on PO line must be deducted of all moves
            # done after the cutoff date.
            moves_after = line.move_ids.filtered(
                lambda r: r.state == 'done' and r.date > self.cutoff_date)
            for move in moves_after:
                if move.product_uom != line.product_uom:
                    received_qty -= move.product_uom._compute_quantity(
                        move.product_uom_qty, line.product_uom)
                else:
                    received_qty -= move.product_uom_qty

        elif self.type == 'accrued_revenue':
            # Processing sale order line
            analytic_account_id = line.order_id.project_id.id or False
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id
            taxes = fpos.map_tax(taxes)

        invoiced_qty = []
        for il in line.invoice_lines:
            if ((il.invoice_id.date or il.invoice_id.date_invoice) <=
                    self.cutoff_date):
                sign = -1 if il.invoice_id.type == 'in_refund' else 1
                invoiced_qty.append((0, 0, {
                    'invoice_line_id': il.id,
                    'quantity': il.quantity * sign,
                    }))

        res = {
            'product_id': line.product_id.id,
            'parent_id': self.id,
            'partner_id': partner.id,
            'name': line.name,
            'account_id': account_id,
            'cutoff_account_id': accrual_account_id,
            'analytic_account_id': analytic_account_id,
            'currency_id': line.currency_id.id,
            'price_unit': price_unit,
            'tax_ids': [(6, 0, [tax.id for tax in taxes])],
            'received_qty': received_qty,
            'invoiced_qty_ids': invoiced_qty,
        }

        if self.type == 'accrued_revenue':
            res['sale_line_id'] = line.id
        elif self.type == 'accrued_expense':
            res['purchase_line_id'] = line.id

        return res

    def get_lines(self):
        res = super(AccountCutoff, self).get_lines()
        if self.type == 'accrued_revenue':
            lines = self.env['sale.order.line'].search([
                ['qty_to_invoice', '!=', 0],
            ])
        elif self.type == 'accrued_expense':
            lines = self.env['purchase.order.line'].search(
                [('qty_to_invoice', '!=', 0)]
            )
        else:
            return res

        for line in lines:
            self.env['account.cutoff.line'].create(
                self._prepare_line(line))

    @api.model
    def _cron_cutoff(self, type):
        # Cron is expected to run at begin of new period. We need the last day
        # of previous month. Support some time difference and compute last day
        # of previous period.
        last_day = datetime.today()
        if last_day.day > 20:
            last_day += relativedelta(months=1)
        last_day = last_day.replace(day=1)
        last_day -= relativedelta(days=1)
        cutoff = self.with_context(type=type).create({
            'cutoff_date': last_day,
            'type': type,
            'auto_reverse': True,
            })
        cutoff.get_lines()

    @api.model
    def _cron_cutoff_expense(self):
        self._cron_cutoff('accrued_expense')

    @api.model
    def _cron_cutoff_revenue(self):
        self._cron_cutoff('accrued_revenue')


class AccountCutoffLine(models.Model):
    _inherit = 'account.cutoff.line'

    sale_line_id = fields.Many2one(
        comodel_name='sale.order.line',
        string='Sale Order Line',
        readonly=True
    )
    purchase_line_id = fields.Many2one(
        comodel_name='purchase.order.line',
        string='Purchase Order Line',
        readonly=True
    )
    order_id = fields.Char(
        'Order',
        compute='_compute_order_id',
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        readonly=True
    )
    received_qty = fields.Float(
        'Received Quantity',
        readonly=True)
    invoiced_qty_ids = fields.One2many(
        'account.cutoff.line.invoice', 'cutoff_line_id',
        'Invoice Lines',
        readonly=True,
    )
    invoiced_qty = fields.Float(
        'Invoiced Quantity',
        compute='_get_invoiced_qty',
        store=True)

    @api.depends('invoiced_qty_ids.quantity')
    def _get_invoiced_qty(self):
        for rec in self:
            rec.invoiced_qty = sum(rec.invoiced_qty_ids.mapped('quantity'))

    @api.constrains('invoiced_qty')
    def _update_invoiced_qty(self):
        for rec in self:
            rec.quantity = rec.received_qty - rec.invoiced_qty

    @api.depends('sale_line_id', 'purchase_line_id')
    def _compute_order_id(self):
        for rec in self:
            if rec.sale_line_id:
                rec.order_id = rec.sale_line_id.order_id.name
            elif rec.purchase_line_id:
                rec.order_id = rec.purchase_line_id.order_id.name

    @api.constrains('quantity')
    def _calc_cutoff_amount(self):
        company = self.env.user.company_id
        for rec in self:
            if not rec.purchase_line_id and not rec.sale_line_id:
                continue
            tax_line_ids = [(5, 0, 0)]
            tax_res = rec.tax_ids.compute_all(
                rec.price_unit, rec.currency_id, rec.quantity,
                rec.product_id, rec.partner_id)
            amount = tax_res['total_excluded']
            if rec.parent_id.type == 'accrued_expense':
                amount = amount * -1
                tax_account_field_name = 'account_accrued_expense_id'
                tax_account_field_label = 'Accrued Expense Tax Account'
            elif rec.parent_id.type == 'accrued_revenue':
                tax_account_field_name = 'account_accrued_revenue_id'
                tax_account_field_label = 'Accrued Revenue Tax Account'
            for tax_line in tax_res['taxes']:
                tax_read = rec.env['account.tax'].browse(tax_line['id'])
                tax_accrual_account_id = tax_read[tax_account_field_name]
                if not tax_accrual_account_id:
                    if not company.accrual_taxes:
                        continue
                    raise UserError(
                        _("Error: Missing '%s' on tax '%s'.")
                        % (tax_account_field_label, tax_read['name']))
                else:
                    tax_accrual_account_id = tax_accrual_account_id[0]
                if rec.parent_id.type == 'accrued_expense':
                    tax_line['amount'] = tax_line['amount'] * -1
                if rec.company_currency_id != rec.currency_id:
                    currency_at_date = rec.currency_id.with_context(
                        date=rec.parent_id.cutoff_date)
                    tax_accrual_amount = currency_at_date.compute(
                        tax_line['amount'], rec.company_currency_id)
                else:
                    tax_accrual_amount = tax_line['amount']
                tax_line_ids.append((0, 0, {
                    'tax_id': tax_line['id'],
                    'base': rec.env['res.currency'].round(
                        rec.price_unit * rec.quantity),
                    'amount': tax_line['amount'],
                    'sequence': tax_line['sequence'],
                    'cutoff_account_id': tax_accrual_account_id.id,
                    'cutoff_amount': tax_accrual_amount,
                    'analytic_account_id': tax_line['analytic'],
                    # tax_line['account_analytic_collected_id'],
                    # account_analytic_collected_id is for invoices IN and OUT
                }))
            if rec.company_currency_id != rec.currency_id:
                currency_at_date = rec.currency_id.with_context(
                    date=rec.cutoff_date)
                amount_company_currency = currency_at_date.compute(
                    amount, rec.company_currency_id)
            else:
                amount_company_currency = amount
            rec.write({
                'amount': amount,
                'cutoff_amount': amount_company_currency,
                'tax_line_ids': tax_line_ids,
            })


class AccountCutoffLineInvoice(models.Model):
    _name = 'account.cutoff.line.invoice'

    cutoff_line_id = fields.Many2one(
        'account.cutoff.line',
        'Cutoff Line',
        required=True,
        ondelete='cascade',
        )
    invoice_line_id = fields.Many2one(
        'account.invoice.line',
        'Invoice Line',
        required=True,
        ondelete='restrict',
        )
    invoice_id = fields.Many2one(
        related='invoice_line_id.invoice_id')
    quantity = fields.Float('Quantity')
