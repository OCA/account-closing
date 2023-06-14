# Copyright 2023 Giuseppe Borruso <gborruso@dinamicheaziendali.it>
# @author: Giuseppe Borruso <gborruso@dinamicheaziendali.it>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def update_account_type(env, table):
    openupgrade.logged_query(
        env.cr,
        f"""
            ALTER TABLE {table}
            ADD COLUMN IF NOT EXISTS account_type VARCHAR
        """,
    )
    openupgrade.logged_query(
        env.cr,
        f"""
            WITH account_type_map AS (
                SELECT
                    res_id AS user_type_id,
                    CASE
                        WHEN name = 'data_account_type_receivable' THEN 'asset_receivable'
                        WHEN name = 'data_account_type_liquidity' THEN 'asset_cash'
                        WHEN name = 'data_account_type_current_assets' THEN 'asset_current'
                        WHEN name = 'data_account_type_non_current_assets'
                            THEN 'asset_non_current'
                        WHEN name = 'data_account_type_fixed_assets' THEN 'asset_fixed'
                        WHEN name = 'data_account_type_expenses' THEN 'expense'
                        WHEN name = 'data_account_type_depreciation' THEN 'expense_depreciation'
                        WHEN name = 'data_account_type_direct_costs' THEN 'expense_direct_cost'
                        WHEN name = 'data_account_off_sheet' THEN 'off_balance'
                        WHEN name = 'data_account_type_payable' THEN 'liability_payable'
                        WHEN name = 'data_account_type_credit_card' THEN 'liability_credit_card'
                        WHEN name = 'data_account_type_prepayments' THEN 'asset_prepayments'
                        WHEN name = 'data_account_type_current_liabilities'
                            THEN 'liability_current'
                        WHEN name = 'data_account_type_non_current_liabilities'
                            THEN 'liability_non_current'
                        WHEN name = 'data_account_type_equity' THEN 'equity'
                        WHEN name = 'data_unaffected_earnings' THEN 'equity_unaffected'
                        WHEN name = 'data_account_type_revenue' THEN 'income'
                        WHEN name = 'data_account_type_other_income' THEN 'income_other'
                        ELSE ''
                    END AS account_type
                FROM ir_model_data
                WHERE module = 'account' AND model = 'account.account.type'
            )
            UPDATE {table} aa
            SET account_type = atm.account_type
            FROM account_type_map atm
            WHERE atm.user_type_id = aa.user_type_id
        """,
    )


@openupgrade.migrate()
def migrate(env, version):

    update_account_type(env, "account_fiscalyear_closing_type_template")
    update_account_type(env, "account_fiscalyear_closing_type")
