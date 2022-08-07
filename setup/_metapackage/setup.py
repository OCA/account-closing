import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-account-closing",
    description="Meta package for oca-account-closing Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-account_cutoff_accrual_picking>=15.0dev,<15.1dev',
        'odoo-addon-account_cutoff_accrual_subscription>=15.0dev,<15.1dev',
        'odoo-addon-account_cutoff_base>=15.0dev,<15.1dev',
        'odoo-addon-account_cutoff_start_end_dates>=15.0dev,<15.1dev',
        'odoo-addon-account_invoice_start_end_dates>=15.0dev,<15.1dev',
        'odoo-addon-account_multicurrency_revaluation>=15.0dev,<15.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 15.0',
    ]
)
