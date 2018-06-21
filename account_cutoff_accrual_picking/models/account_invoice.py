# -*- coding: utf-8 -*-
# Copyright 2018 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, _
from odoo.exceptions import UserError


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    def _update_cutoff_expense(self):
        # Look for lines where cutoff is missing or needs to be update
        self.env.cr.execute("""
            SELECT ail.id,
                ac.state,
                ac.id as cutoff_id,
                acl.id as cutoff_line_id,
                acli.id as cutoff_line_invoice_id
            FROM account_invoice_line ail
            JOIN account_invoice ai
                ON ail.invoice_id=ai.id
            JOIN account_cutoff ac
                ON COALESCE(ai.date, ai.date_invoice) <= ac.cutoff_date
                AND ac.type='accrued_expense'
            LEFT JOIN account_cutoff_line acl
                ON acl.parent_id=ac.id
                AND ail.purchase_line_id=acl.purchase_line_id
            LEFT JOIN account_cutoff_line_invoice acli
                ON acli.cutoff_line_id=acl.id and acli.invoice_line_id=ail.id
            WHERE ail.purchase_line_id is not NULL
            AND ail.id in %s
            AND (acli.quantity is NULL
                OR acli.quantity != ail.quantity * (
                    CASE WHEN ai.type = 'in_refund' THEN -1 ELSE 1 END))
          """, (tuple(self.ids), ))
        data = self.env.cr.dictfetchall()
        for row in data:
            if row['state'] == 'done':
                raise UserError(_(
                    "You cannot validate an invoice for an accounting date "
                    "where the cutoff accounting entry has already been "
                    "created"))
            invoice_line = self.browse(row['id'])
            acl_id = row['cutoff_line_id']
            acli_id = row['cutoff_line_invoice_id']
            if acli_id:
                # The quantity on the invoice has changed since cutoff
                # generation
                acli = self.env['account.cutoff.line.invoice'].browse(acli_id)
                sign = -1 if invoice_line.invoice_id.type == 'in_refund' else 1
                acli.quantity = invoice_line.quantity * sign
            elif acl_id:
                # The invoice has been created after the cutoff generation
                acl = self.env['account.cutoff.line'].browse(acl_id)
                sign = -1 if invoice_line.invoice_id.type == 'in_refund' else 1
                acl.write({
                    'invoiced_qty_ids': [(0, 0, {
                        'invoice_line_id': invoice_line.id,
                        'quantity': invoice_line.quantity * sign,
                        })],
                    })
            else:
                # No cutoff entry yet for this line
                ac = self.env['account.cutoff'].browse(row['cutoff_id'])
                self.env['account.cutoff.line'].create(
                    ac._prepare_line(invoice_line.purchase_line_id))


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def invoice_validate(self):
        self.filtered(lambda r: r.type in ('in_refund', 'in_invoice')).\
            invoice_line_ids._update_cutoff_expense()
        return super(AccountInvoice, self).invoice_validate()

    def unlink(self):
        acli = self.env['account.cutoff.line.invoice'].search(
            [('invoice_line_id', 'in', self.mapped('invoice_line_ids').ids)])
        if acli:
            if 'done' in acli.mapped('cutoff_line_id.parent_id.state'):
                raise UserError(_(
                    "You cannot delete an invoice for an accounting date "
                    "where the cutoff accounting entry has already been "
                    "created"))
            acli.unlink()
        return super(AccountInvoice, self).unlink()
