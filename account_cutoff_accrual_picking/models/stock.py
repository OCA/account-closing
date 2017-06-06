# -*- coding: utf-8 -*-
# © 2013-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # I know, in v8, there is a M2M from pickings to invoice
    # (in v7, it was a many2one), so we can have several invoice dates
    # But, in real life, one invoice date should be enough
    max_date_invoice = fields.Date(
        compute='compute_date_invoice', string='Invoice Date',
        store=True, readonly=True)
    # picking_type_code is refined in the stock module
    picking_type_code = fields.Selection(
        related='picking_type_id.code', store=True, readonly=True)

    @api.one
    @api.depends('invoice_ids.date_invoice', 'invoice_ids.state')
    def compute_date_invoice(self):
        max_date_invoice = False
        for inv in self.invoice_ids:
            if (
                    inv.state in ('open', 'paid') and
                    inv.date_invoice > max_date_invoice):
                max_date_invoice = inv.date_invoice
        self.max_date_invoice = max_date_invoice
