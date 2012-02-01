# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Camptocamp SA (http://www.camptocamp.com)
# All Right Reserved
#
# Author : Yannick Vaucher (Camptocamp)
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields

class ResCompany(osv.osv):
    _inherit="res.company"
    
    _columns = {'reevaluation_loss_account_id': fields.many2one('account.account',
                                                                'Reevaluation loss account',
                                                                domain=[('type','=','other')]),
                'reevaluation_gain_account_id': fields.many2one('account.account',
                                                                'Reevaluation gain account',
                                                                domain=[('type','=','other')]),
                'provision_bs_loss_account_id': fields.many2one('account.account',
                                                                'Provision B.S loss account',
                                                                domain=[('type','=','other')]),
                'provision_bs_gain_account_id': fields.many2one('account.account',
                                                                'Provision B.S gain account',
                                                                domain=[('type','=','other')]),
                'provision_pl_loss_account_id': fields.many2one('account.account',
                                                                'Provision P&L loss account',
                                                                domain=[('type','=','other')]),
                'provision_pl_gain_account_id': fields.many2one('account.account',
                                                                'Provision P&L gain account',
                                                                domain=[('type','=','other')])}


ResCompany()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
