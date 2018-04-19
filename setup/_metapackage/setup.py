import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo8-addons-oca-account-closing",
    description="Meta package for oca-account-closing Odoo addons",
    version=version,
    install_requires=[
        'odoo8-addon-account_cutoff_accrual_base',
        'odoo8-addon-account_cutoff_accrual_picking',
        'odoo8-addon-account_cutoff_base',
        'odoo8-addon-account_cutoff_prepaid',
        'odoo8-addon-account_invoice_accrual',
        'odoo8-addon-account_multicurrency_revaluation',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
