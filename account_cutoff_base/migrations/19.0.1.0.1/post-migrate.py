# Copyright 2024 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

import odoo

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info("Remove constraint on account cutoff")
    odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

    cr.execute(
        """
        ALTER TABLE account_cutoff
        DROP CONSTRAINT IF EXISTS account_cutoff_date_type_company_uniq
    """
    )
