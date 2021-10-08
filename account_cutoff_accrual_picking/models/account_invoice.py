# -*- coding: utf-8 -*-
# Copyright 2018-2021 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, _
from odoo.exceptions import UserError


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    def _update_cutoff(self):
        if not self:
            return
        # Look for lines where cutoff is missing or needs to be update
        self.env.cr.execute(
            """
            SELECT ail.id,
                ac.state,
                ac.id as cutoff_id,
                acl.id as cutoff_line_id,
                acli.id as cutoff_line_invoice_id
            FROM account_invoice_line ail
            LEFT JOIN sale_order_line_invoice_rel ailsolrel
              ON ailsolrel.invoice_line_id = ail.id
            JOIN account_invoice ai
              ON ail.invoice_id=ai.id
            JOIN account_cutoff ac
              ON COALESCE(ai.date, ai.date_invoice) <= ac.cutoff_date
              AND (
                (ai.type in ('in_invoice', 'in_refund')
                    AND ac.type='accrued_expense')
                OR
                (ai.type in ('out_invoice', 'out_refund')
                    AND ac.type='accrued_revenue')
              )
            LEFT JOIN account_cutoff_line acl
              ON acl.parent_id=ac.id
              AND (
                (ac.type='accrued_expense'
                    AND ail.purchase_line_id=acl.purchase_line_id)
                OR
                (ac.type='accrued_revenue'
                    AND ailsolrel.order_line_id=acl.sale_line_id)
              )
            LEFT JOIN account_cutoff_line_invoice acli
              ON acli.cutoff_line_id=acl.id and acli.invoice_line_id=ail.id
            WHERE
              ail.id in %s
              AND (
                (ac.type='accrued_expense'
                    AND ail.purchase_line_id is not NULL)
                OR
                (ac.type='accrued_revenue'
                    AND ailsolrel.order_line_id is not NULL)
              )
              AND (acli.quantity is NULL
                OR acli.quantity != ail.quantity * (
                  CASE WHEN ai.type in ('in_refund', 'out_refund') THEN -1 ELSE 1 END))
          """,
            (tuple(self.ids),),
        )
        data = self.env.cr.dictfetchall()
        for row in data:
            if row["state"] == "done":
                raise UserError(
                    _(
                        "You cannot validate an invoice for an accounting date "
                        "where the cutoff accounting entry has already been "
                        "created"
                    )
                )
            invoice_line = self.browse(row["id"])
            acl_id = row["cutoff_line_id"]
            acli_id = row["cutoff_line_invoice_id"]
            if acli_id:
                # The quantity on the invoice has changed since cutoff
                # generation
                acli = self.env["account.cutoff.line.invoice"].browse(acli_id)
                if invoice_line.invoice_id.type in ("in_refund", "out_refund"):
                    sign = -1
                else:
                    sign = 1
                acli.quantity = invoice_line.quantity * sign
            elif acl_id:
                # The invoice has been created after the cutoff generation
                acl = self.env["account.cutoff.line"].browse(acl_id)
                if invoice_line.invoice_id.type in ("in_refund", "out_refund"):
                    sign = -1
                else:
                    sign = 1
                acl.write(
                    {
                        "invoiced_qty_ids": [
                            (
                                0,
                                0,
                                {
                                    "invoice_line_id": invoice_line.id,
                                    "quantity": invoice_line.quantity * sign,
                                },
                            )
                        ],
                    }
                )
            else:
                # No cutoff entry yet for this line
                ac = self.env["account.cutoff"].browse(row["cutoff_id"])
                if ac.type == "accrued_revenue":
                    for sol in invoice_line.sale_line_ids:
                        data = ac._prepare_line(sol)
                        if data:
                            self.env["account.cutoff.line"].create(data)
                elif ac.type == "accrued_expense":
                    data = ac._prepare_line(invoice_line.purchase_line_id)
                    if data:
                        self.env["account.cutoff.line"].create(data)


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    def invoice_validate(self):
        res = super(AccountInvoice, self).invoice_validate()
        self.invoice_line_ids._update_cutoff()
        return res

    def unlink(self):
        acli = self.env["account.cutoff.line.invoice"].search(
            [("invoice_line_id", "in", self.mapped("invoice_line_ids").ids)]
        )
        if acli:
            if "done" in acli.mapped("cutoff_line_id.parent_id.state"):
                raise UserError(
                    _(
                        "You cannot delete an invoice for an accounting date "
                        "where the cutoff accounting entry has already been "
                        "created"
                    )
                )
            acli.unlink()
        return super(AccountInvoice, self).unlink()
