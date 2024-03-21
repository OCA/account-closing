# Copyright 2023 Giuseppe Borruso <gborruso@dinamicheaziendali.it>
# @author: Giuseppe Borruso <gborruso@dinamicheaziendali.it>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def update_account_type(env, model, new_type, old_type):
    openupgrade.logged_query(
        env.cr,
        """
            UPDATE %(model)s
            SET account_type = '%(new_type)s'
            WHERE id in (
                SELECT id
                WHERE account_type_id = %(old_type)s
            )
        """
        % {
            "model": model,
            "new_type": new_type,
            "old_type": old_type,
        },
    )


@openupgrade.migrate()
def migrate(env, version):

    all_account_type = [
        ("asset_receivable", env.ref("account.data_account_type_receivable").id),
        ("asset_cash", env.ref("account.data_account_type_liquidity").id),
        ("asset_current", env.ref("account.data_account_type_current_assets").id),
        (
            "asset_non_current",
            env.ref("account.data_account_type_non_current_assets").id,
        ),
        ("asset_fixed", env.ref("account.data_account_type_fixed_assets").id),
        ("expense", env.ref("account.data_account_type_expenses").id),
        ("expense_depreciation", env.ref("account.data_account_type_depreciation").id),
        ("expense_direct_cost", env.ref("account.data_account_type_direct_costs").id),
        ("off_balance", env.ref("account.data_account_off_sheet").id),
        ("liability_payable", env.ref("account.data_account_type_payable").id),
        ("liability_credit_card", env.ref("account.data_account_type_credit_card").id),
        ("asset_prepayments", env.ref("account.data_account_type_prepayments").id),
        (
            "liability_current",
            env.ref("account.data_account_type_current_liabilities").id,
        ),
        (
            "liability_non_current",
            env.ref("account.data_account_type_non_current_liabilities").id,
        ),
        ("equity", env.ref("account.data_account_type_equity").id),
        ("equity_unaffected", env.ref("account.data_unaffected_earnings").id),
        ("income", env.ref("account.data_account_type_revenue").id),
        ("income_other", env.ref("account.data_account_type_other_income").id),
    ]

    for new_type, old_type in all_account_type:
        update_account_type(
            env, "account_fiscalyear_closing_type_template", new_type, old_type
        )
        update_account_type(env, "account_fiscalyear_closing_type", new_type, old_type)
