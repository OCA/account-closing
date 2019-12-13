# coding: utf-8
# Copyright 2019 Opener B.V.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """ UPDATE XML ID after typo fixed """
    if not version:
        return
    cr.execute(
        """ UPDATE ir_model_data
        SET name = 'group_revaluation_additional'
        WHERE module = 'account_multicurrency_revaluation'
            AND name = 'group_revaluation_additonal' """)
