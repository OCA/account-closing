import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo10-addons-oca-account-closing",
    description="Meta package for oca-account-closing Odoo addons",
    version=version,
    install_requires=[
        'odoo10-addon-account_cutoff_accrual_base',
        'odoo10-addon-account_cutoff_accrual_dates',
        'odoo10-addon-account_cutoff_base',
        'odoo10-addon-account_cutoff_prepaid',
        'odoo10-addon-account_fiscal_year_closing',
        'odoo10-addon-account_invoice_start_end_dates',
        'odoo10-addon-account_multicurrency_revaluation',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
