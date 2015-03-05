# -*- coding: utf-8 -*-
#
#
#    Authors: Laetitia Gangloff
#    Copyright (c) 2014 Acsone SA/NV (http://www.acsone.eu)
#    All Rights Reserved
#
#    WARNING: This program as such is intended to be used by professional
#    programmers who take the whole responsibility of assessing all potential
#    consequences resulting from its eventual inadequacies and bugs.
#    End users who are looking for a ready-to-use solution with commercial
#    guarantees and support are strongly advised to contact a Free Software
#    Service Company.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

from openerp.osv import fields, orm


class res_partner(orm.Model):
    _inherit = 'res.partner'

    _columns = {
        'property_account_supplier_accrual': fields.property(
            model='account.account',
            type='many2one',
            relation='account.account',
            string="Accrual Account Supplier",
            domain="[('type', '=', 'payable')]",
            help="This account will be used instead of the default one as \
                the supplier accrual account for the current partner",
            required=True),
        'property_account_customer_accrual': fields.property(
            model='account.account',
            type='many2one',
            relation='account.account',
            string="Accrual Account Customer",
            domain="[('type', '=', 'receivable')]",
            help="This account will be used instead of the default one as \
                the customer accrual account for the current partner",
            required=True),
        'property_journal_accrual': fields.property(
            model='account.journal',
            type='many2one',
            relation='account.journal',
            string="Accrual Journal",
            domain="[('type', '=', 'general')]",
            help="This journal will be used as the default one for accrual \
                operation for the current partner",
            required=True),
    }

    def _commercial_fields(self, cr, uid, context=None):
        return super(res_partner, self)._commercial_fields(
            cr, uid, context=context) + ['property_account_supplier_accrual',
                                         'property_account_customer_accrual',
                                         'property_journal_accrual']
