# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# Copyright 2018 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    qty_to_invoice = fields.Float(
        compute='_compute_qty_to_invoice',
        store=True
    )

    @api.depends('qty_received', 'qty_invoiced')
    def _compute_qty_to_invoice(self):
        for rec in self:
            rec.qty_to_invoice = rec.qty_received - rec.qty_invoiced

    account_cutoff_line_ids = fields.One2many(
        'account.cutoff.line', 'purchase_line_id',
        string='Account Cutoff Lines',
        readonly=True)
