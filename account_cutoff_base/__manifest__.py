# Copyright 2013-2016 Akretion
# Copyright 2018 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Account Cut-off Base',
    'version': '12.0.1.0.1',
    'category': 'Accounting & Finance',
    'license': 'AGPL-3',
    'summary': 'Base module for Account Cut-offs',
    'author': 'Akretion,Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/account-closing',
    'depends': [
        'account',
    ],
    'data': [
        'security/account_cutoff_base_security.xml',
        'security/ir.model.access.csv',
        'views/account_cutoff.xml',
        'views/res_config_settings.xml',
    ],
    'installable': True,
}
