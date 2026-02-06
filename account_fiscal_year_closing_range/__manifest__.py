{
    "name": "Account Fiscal Year Closing Range",
    "summary": "Allow mapping account ranges in fiscal year closing",
    "version": "18.0.1.0.0",
    "category": "Accounting & Finance",
    "website": "https://github.com/OCA/account-closing",
    "author": "Escodoo, Odoo Community Association (OCA)",
    "maintainers": ["kaynnan, marcelsavegnago"],
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "account_fiscal_year_closing",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_fiscalyear_closing_views.xml",
        "views/account_fiscalyear_closing_template_views.xml",
        "wizards/mapping_range_wizard.xml",
    ],
}
