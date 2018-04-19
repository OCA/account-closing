import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo9-addons-oca-account-closing",
    description="Meta package for oca-account-closing Odoo addons",
    version=version,
    install_requires=[
        'odoo9-addon-account_cutoff_base',
        'odoo9-addon-account_cutoff_prepaid',
        'odoo9-addon-account_fiscal_year_closing',
        'odoo9-addon-account_invoice_start_end_dates',
        'odoo9-addon-account_multicurrency_revaluation',
        'odoo9-addon-account_multicurrency_revaluation_report',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
