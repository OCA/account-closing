# Copyright 2018 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, _
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def do_merge(self, keep_references=True, date_invoice=False,
                 remove_empty_invoice_lines=True):
        invoices_info = super(AccountInvoice, self).do_merge()
        for new_invoice_id, old_invoice_ids in invoices_info.iteritems():
            old_invoices = self.browse(old_invoice_ids)
            to_be_reversed = old_invoices.mapped('to_be_reversed')
            if len(to_be_reversed) > 1:
                raise UserError(_(
                    "You cannot merge invoices where only some of them have "
                    "an accrual entry"))
            elif to_be_reversed == ["True"]:
                old_invoices.reverse_accruals()
                new_invoice = self.browse(new_invoice_id)
                accrual = self.env['account.move.accrue'].with_context(
                    active_model=self._name, active_ids=new_invoice.ids)\
                    .create()
                accrual.action_accrue()
        return invoices_info
