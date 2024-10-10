# Copyright 2023 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)


def post_init_hook(cr, registry):
    cr.execute(
        """
        UPDATE sale_order_line
        SET is_cutoff_accrual_excluded = TRUE
        WHERE order_id IN
        ( SELECT id FROM sale_order WHERE force_invoiced )
    """
    )
