import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo14-addons-oca-account-closing",
    description="Meta package for oca-account-closing Odoo addons",
    version=version,
    install_requires=[
        'odoo14-addon-account_cutoff_accrual_picking',
        'odoo14-addon-account_cutoff_accrual_subscription',
        'odoo14-addon-account_cutoff_base',
        'odoo14-addon-account_cutoff_start_end_dates',
        'odoo14-addon-account_invoice_start_end_dates',
        'odoo14-addon-account_multicurrency_revaluation',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 14.0',
    ]
)
