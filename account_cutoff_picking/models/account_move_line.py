# Copyright 2018-2021 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_messing_cutoff(self):
        # Look for lines where cutoff is missing or needs to be update
        self.env.cr.execute(
            """
            SELECT aml.id,
                ac.state,
                ac.id as cutoff_id,
                acl.id as cutoff_line_id,
                acli.id as cutoff_line_invoice_id
            FROM account_move_line aml
            LEFT JOIN sale_order_line_invoice_rel ailsolrel
              ON ailsolrel.invoice_line_id = aml.id
            JOIN account_move am
              ON aml.move_id=am.id
            JOIN account_cutoff ac
              ON COALESCE(am.date, am.invoice_date) <= ac.cutoff_date
              AND (
                (am.move_type in ('in_invoice', 'in_refund')
                    AND ac.cutoff_type='accrued_expense')
                OR
                (am.move_type in ('out_invoice', 'out_refund')
                    AND ac.cutoff_type='accrued_revenue')
              )
            LEFT JOIN account_cutoff_line acl
              ON acl.parent_id=ac.id
              AND (
                (ac.cutoff_type='accrued_expense'
                    AND aml.purchase_line_id=acl.purchase_line_id)
                OR
                (ac.cutoff_type='accrued_revenue'
                    AND ailsolrel.order_line_id=acl.sale_line_id)
              )
            LEFT JOIN account_cutoff_line_invoice acli
              ON acli.cutoff_line_id=acl.id and acli.move_line_id=aml.id
            WHERE
              aml.id in %s
              AND (
                (ac.cutoff_type='accrued_expense'
                    AND aml.purchase_line_id is not NULL)
                OR
                (ac.cutoff_type='accrued_revenue'
                    AND ailsolrel.order_line_id is not NULL)
              )
              AND (acli.quantity is NULL
                OR acli.quantity != aml.quantity * (
                  CASE WHEN am.move_type in ('in_refund', 'out_refund') THEN -1 ELSE 1 END))
          """,
            (tuple(self.ids),),
        )
        return self.env.cr.dictfetchall()

    def _update_cutoff(self):
        if not self:
            return

        for row in self._get_messing_cutoff():
            if row["state"] == "done":
                raise UserError(
                    _(
                        "You cannot validate an invoice for an accounting date "
                        "that modifies a closed cutoff (i.e. for which an "
                        "accounting entry has already been created)"
                    )
                )
            move_line = self.browse(row["id"])
            acl_id = row["cutoff_line_id"]
            acli_id = row["cutoff_line_invoice_id"]
            if acli_id:
                # The quantity on the invoice has changed since cutoff
                # generation
                self.env["account.cutoff.line.invoice"].browse(
                    acli_id
                )._update_quantity(move_line)
            elif acl_id:
                # The invoice has been created after the cutoff generation
                self.env["account.cutoff.line"].browse(acl_id)._add_move_line(move_line)
            else:
                # No cutoff entry yet for this line
                self.env["account.cutoff"].browse(row["cutoff_id"])._add_move_line(
                    move_line
                )
