# Copyright 2021 Alex Comba - Agile Business Group
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_field_renames = [
    ("account.cutoff", "account_cutoff", "type", "cutoff_type"),
]


@openupgrade.migrate()
def migrate(env, version):
    if not version:
        return
    openupgrade.rename_fields(env, _field_renames)
