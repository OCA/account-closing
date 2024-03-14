# Copyright 2021 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountCutoff(models.Model):
    _inherit = "account.cutoff"

    def _get_merge_keys(self):
        """Return merge criteria for provision lines

        The returned list must contain valid field names
        for account.move.line. Provision lines with the
        same values for these fields will be merged.
        The list must at least contain account_id.
        """
        res = super()._get_merge_keys()
        if "categ_id" not in res:
            res.append("categ_id")
        return res

    def _prepare_provision_line(self, cutoff_line):
        res = super()._prepare_provision_line(cutoff_line)
        res["categ_id"] = cutoff_line.product_id.categ_id.id
        return res
