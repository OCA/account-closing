# Copyright 2026 Lorenzo Battistini
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Cut-off Spanning Start End Dates",
    "version": "18.0.1.0.0",
    "category": "Accounting & Finance",
    "license": "AGPL-3",
    "summary": "Separate account for the accruals spanning the cut-off date",
    "author": "Lorenzo Battistini, Odoo Community Association (OCA)",
    "maintainers": ["eLBati"],
    "website": "https://github.com/OCA/account-closing",
    "depends": ["account_cutoff_start_end_dates"],
    "data": [
        "views/account_cutoff.xml",
        "views/account_cutoff_line.xml",
        "views/res_config_settings.xml",
    ],
    "installable": True,
}
