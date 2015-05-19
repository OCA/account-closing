# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2015 - Present Savoir-faire Linux
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
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import orm
from openerp.tools.translate import _


class account_move(orm.Model):

    _inherit = 'account.move'

    def _check_period(self, cr, uid, ids, context=None):
        """
        Cannot create journal entries with closed period
        """
        for move in self.browse(cr, uid, ids, context=context):
            if move.period_id.state != 'draft':
                    return False
        return True

    def _check_period_msg(self, cr, uid, ids, context=None):
        """Return message for check_period """
        return _(
            'You try to save a journal item with a closed period; '
            'please change your period or contact your responsible account'
        )

    _constraints = [
        (_check_period,
         _check_period_msg,
         ['period_id'])
    ]
