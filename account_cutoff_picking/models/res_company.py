# Copyright 2020-2021 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    default_cutoff_picking_interval_days = fields.Integer(
        string="Analysis Interval",
        help="To generate the accrual/prepaid revenue/expenses based on picking "
        "dates vs invoice dates, Odoo will analyse all the pickings/invoices from "
        "N days before the cutoff date up to the cutoff date. "
        "N is the Analysis Interval. If you increase the analysis interval, "
        "Odoo will take more time to generate the cutoff lines.",
        default=90,
    )

    _sql_constraints = [
        (
            "cutoff_picking_interval_days_positive",
            "CHECK(default_cutoff_picking_interval_days > 0)",
            "The value of the field 'Analysis Interval' must be strictly positive.",
        )
    ]
