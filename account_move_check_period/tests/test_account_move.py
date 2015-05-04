# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2015 Savoir-faire Linux
#    (<http://www.savoirfairelinux.com>).
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
##############################################################################

from openerp.tests.common import TransactionCase
from openerp.osv.orm import except_orm
from datetime import datetime


class test_account_move(TransactionCase):

    def setUp(self):
        super(test_account_move, self).setUp()
        self.move_obj = self.registry('account.move')
        self.user_model = self.registry("res.users")
        self.period_model = self.registry("account.period")
        # Get context
        self.context = self.user_model.context_get(self.cr, self.uid)
        self.date = datetime.now()
        self.period_id = self.period_model.find(
            self.cr, self.uid, self.date,
            context={'account_period_prefer_normal': True})[0]
        self.vals = {
            'journal_id': self.ref('account.sales_journal'),
            'period_id': self.period_id,
            'date': self.date,
        }

    def test_create_move(self):
        cr, uid, vals = self.cr, self.uid, self.vals.copy()
        context = self.context
        self.period_model.write(
            cr, uid, self.period_id, {
                'state': 'done',
            }, context=context)
        with self.assertRaises(except_orm):
            self.move_obj.create(cr, uid, vals, context=context)
