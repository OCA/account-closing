# Copyright 2025 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def company_country_cutoff_setup(env):
    companies = env["res.company"].search([("account_fiscal_country_id", "!=", False)])
    for company in companies:
        company._country_cutoff_setup()
