# Copyright 2023 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    if not openupgrade.column_exists(
        env.cr, "res_company", "default_cutoff_picking_interval_days"
    ):
        openupgrade.rename_fields(
            env,
            [
                (
                    "res.company",
                    "res_company",
                    "default_cutoff_accrual_picking_interval_days",
                    "default_cutoff_picking_interval_days",
                ),
            ],
        )
