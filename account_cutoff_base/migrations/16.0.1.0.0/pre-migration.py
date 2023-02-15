# Copyright 2023 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    if not openupgrade.column_exists(env.cr, "account_cutoff", "move_ref"):
        openupgrade.rename_fields(
            env,
            [
                (
                    "account.cutoff",
                    "account_cutoff",
                    "move_label",
                    "move_ref",
                ),
            ],
        )
