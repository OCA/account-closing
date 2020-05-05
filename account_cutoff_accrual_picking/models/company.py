# Copyright 2020 Akretion France
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    default_cutoff_accrual_picking_interval_days = fields.Integer(
        string="Picking Analysis Interval",
        help="To generate the accruals based on pickings, Odoo will "
        "analyse all the pickings between the cutoff date and N "
        "days before. N is the Picking Analysis Interval.",
        default=90,
    )

    _sql_constraints = [
        (
            "cutoff_picking_interval_days_positive",
            "CHECK(default_cutoff_accrual_picking_interval_days > 0)",
            "The value of the field 'Picking Analysis Interval' must "
            "be strictly positive.",
        )
    ]
