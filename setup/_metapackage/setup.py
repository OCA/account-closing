import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-account-closing",
    description="Meta package for oca-account-closing Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-account_cutoff_accrual_order_base>=16.0dev,<16.1dev',
        'odoo-addon-account_cutoff_accrual_order_stock_base>=16.0dev,<16.1dev',
        'odoo-addon-account_cutoff_accrual_purchase>=16.0dev,<16.1dev',
        'odoo-addon-account_cutoff_accrual_purchase_stock>=16.0dev,<16.1dev',
        'odoo-addon-account_cutoff_accrual_sale>=16.0dev,<16.1dev',
        'odoo-addon-account_cutoff_accrual_sale_stock>=16.0dev,<16.1dev',
        'odoo-addon-account_cutoff_accrual_subscription>=16.0dev,<16.1dev',
        'odoo-addon-account_cutoff_base>=16.0dev,<16.1dev',
        'odoo-addon-account_cutoff_picking>=16.0dev,<16.1dev',
        'odoo-addon-account_cutoff_start_end_dates>=16.0dev,<16.1dev',
        'odoo-addon-account_invoice_start_end_dates>=16.0dev,<16.1dev',
        'odoo-addon-account_invoice_start_end_dates_move>=16.0dev,<16.1dev',
        'odoo-addon-account_multicurrency_revaluation>=16.0dev,<16.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 16.0',
    ]
)
