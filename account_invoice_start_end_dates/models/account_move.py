# Copyright 2019-2021 Akretion France (https://akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        for move in self:
            for line in move.line_ids:
                if (
                    line.product_id
                    and line.product_id.must_have_dates
                    and (not line.start_date or not line.end_date)
                ):
                    raise UserError(
                        _(
                            "Missing Start Date and End Date for invoice "
                            "line with Product '%s' which has the "
                            "property 'Must Have Start/End Dates'."
                        )
                        % (line.product_id.display_name)
                    )
        return super()._post(soft=soft)
