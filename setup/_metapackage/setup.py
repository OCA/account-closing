import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo11-addons-oca-account-closing",
    description="Meta package for oca-account-closing Odoo addons",
    version=version,
    install_requires=[
        'odoo11-addon-account_cutoff_accrual_base',
        'odoo11-addon-account_cutoff_base',
        'odoo11-addon-account_cutoff_prepaid',
        'odoo11-addon-account_invoice_start_end_dates',
        'odoo11-addon-account_multicurrency_revaluation',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
