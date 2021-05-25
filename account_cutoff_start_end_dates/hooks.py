# Copyright 2021 Alfredo Zamora - Agile Business Group
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

from odoo import SUPERUSER_ID, api


def module_migration(cr):
    account_cutoff_line_model = "account.cutoff.line"
    account_cutoff_line_table = "account_cutoff_line"
    account_cutoff_prepaid = "account_cutoff_prepaid"
    account_cutoff_accrual_dates = "account_cutoff_accrual_dates"
    account_cutoff_start_end_dates = "account_cutoff_start_end_dates"
    if openupgrade.is_module_installed(cr, account_cutoff_accrual_dates):
        openupgrade.update_module_names(
            cr,
            [
                (account_cutoff_accrual_dates, account_cutoff_start_end_dates),
            ],
            merge_modules=True,
        )
    if openupgrade.is_module_installed(cr, account_cutoff_prepaid):
        openupgrade.update_module_names(
            cr,
            [
                (account_cutoff_prepaid, account_cutoff_start_end_dates),
            ],
            merge_modules=True,
        )
        field_renames = [
            (
                account_cutoff_line_model,
                account_cutoff_line_table,
                "prepaid_days",
                "cutoff_days",
            ),
        ]
        env = api.Environment(cr, SUPERUSER_ID, {})
        openupgrade.rename_fields(env, field_renames)
