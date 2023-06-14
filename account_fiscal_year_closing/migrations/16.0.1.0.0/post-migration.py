# Copyright 2023 Giuseppe Borruso <gborruso@dinamicheaziendali.it>
# @author: Giuseppe Borruso <gborruso@dinamicheaziendali.it>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):

    openupgrade.load_data(
        env.cr,
        "account_fiscal_year_closing",
        "migrations/16.0.1.0.0/noupdate_changes.xml",
    )
