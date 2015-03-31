# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Yannick Vaucher
#    Copyright 2012 Camptocamp SA
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

from openerp.osv import fields, orm


class ResCompany(orm.Model):
    _inherit = "res.company"

    _columns = {
        'revaluation_loss_account_id': fields.many2one(
            'account.account',
            'Revaluation loss account',
            domain=[('type', '=', 'other')]),
        'revaluation_gain_account_id': fields.many2one(
            'account.account',
            'Revaluation gain account',
            domain=[('type', '=', 'other')]),
        'revaluation_analytic_account_id': fields.many2one(
            'account.analytic.account',
            'Revaluation Analytic account'),
        'provision_bs_loss_account_id': fields.many2one(
            'account.account',
            'Provision B.S loss account',
            domain=[('type', '=', 'other')]),
        'provision_bs_gain_account_id': fields.many2one(
            'account.account',
            'Provision B.S gain account',
            domain=[('type', '=', 'other')]),
        'provision_pl_loss_account_id': fields.many2one(
            'account.account',
            'Provision P&L loss account',
            domain=[('type', '=', 'other')]),
        'provision_pl_gain_account_id': fields.many2one(
            'account.account',
            'Provision P&L gain account',
            domain=[('type', '=', 'other')]),
        'provision_pl_analytic_account_id': fields.many2one(
            'account.analytic.account',
            'Provision P&L Analytic account'),
        'default_currency_reval_journal_id': fields.many2one(
            'account.journal',
            'Currency gain & loss Default Journal',
            domain=[('type', '=', 'general')]),
        'reversable_revaluations': fields.boolean(
            'Reversable Revaluations',
            help="Revaluations entries will be created"
                 " as \"To Be Reversed\".")
    }

    _defaults = {
        'reversable_revaluations': True,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
