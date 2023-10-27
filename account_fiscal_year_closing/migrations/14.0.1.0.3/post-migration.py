from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):

    openupgrade.load_data(
        env.cr,
        "account_fiscal_year_closing",
        "migrations/14.0.1.0.3/noupdate_changes.xml",
    )
