import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo13-addons-oca-account-closing",
    description="Meta package for oca-account-closing Odoo addons",
    version=version,
    install_requires=[
        'odoo13-addon-account_cutoff_accrual_base',
        'odoo13-addon-account_cutoff_accrual_dates',
        'odoo13-addon-account_cutoff_accrual_picking',
        'odoo13-addon-account_cutoff_base',
        'odoo13-addon-account_cutoff_prepaid',
        'odoo13-addon-account_invoice_start_end_dates',
        'odoo13-addon-account_multicurrency_revaluation',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
