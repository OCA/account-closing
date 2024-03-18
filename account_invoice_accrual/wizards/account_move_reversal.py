# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMoveReversal(models.TransientModel):

    _inherit = "account.move.reversal"

    def reverse_moves(self):
        self.move_ids.write({"to_be_reversed": False})
        return super().reverse_moves()
