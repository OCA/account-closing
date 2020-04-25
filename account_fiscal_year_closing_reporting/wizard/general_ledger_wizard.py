# Copyright 2020 Sergio Corato <https://github.com/sergiocorato>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class GeneralLedgerReportWizard(models.TransientModel):
    _inherit = "general.ledger.report.wizard"

    exclude_opening = fields.Boolean(default=True)

    def _prepare_report_general_ledger(self):
        res = super()._prepare_report_general_ledger()
        res.update({
            'exclude_opening': self.exclude_opening,
        })
        return res
