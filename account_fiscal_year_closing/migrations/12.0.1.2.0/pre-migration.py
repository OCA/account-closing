# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.logged_query(
        env.cr, """
            UPDATE account_move
                SET closing_type = 'none'
            WHERE closing_type is null;
            """
    )
