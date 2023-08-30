# Copyright 2018-2021 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# Copyright 2013 Alexis de Lattre (Akretion) <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AccountCutoffLineInvoice(models.Model):
    _name = "account.cutoff.line.invoice"
    _description = "account cutoff line invoice"

    cutoff_line_id = fields.Many2one(
        "account.cutoff.line",
        "Cutoff Line",
        required=True,
        ondelete="cascade",
    )
    move_line_id = fields.Many2one(
        "account.move.line",
        "Move Line",
        required=True,
        ondelete="restrict",
    )
    move_id = fields.Many2one(related="move_line_id.move_id")
    quantity = fields.Float()

    def _update_quantity(self, move_line):
        self.ensure_one()
        if move_line.move_id.move_type in ("in_refund", "out_refund"):
            sign = -1
        else:
            sign = 1
        self.quantity = move_line.quantity * sign
