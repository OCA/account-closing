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

from openerp import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    revaluation_loss_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Revaluation loss account',
        domain=[('type', '=', 'other')],
    )
    revaluation_gain_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Revaluation gain account',
        domain=[('type', '=', 'other')],
    )
    revaluation_analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Revaluation Analytic account'
    )
    provision_bs_loss_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Provision B.S loss account',
        domain=[('type', '=', 'other')]
    )
    provision_bs_gain_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Provision B.S gain account',
        domain=[('type', '=', 'other')]
    )
    provision_pl_loss_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Provision P&L loss account',
        domain=[('type', '=', 'other')]
    )
    provision_pl_gain_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Provision P&L gain account',
        domain=[('type', '=', 'other')]
    )
    provision_pl_analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Provision P&L Analytic account'
    )
    default_currency_reval_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Currency gain & loss Default Journal',
        domain=[('type', '=', 'general')]
    )
    reversable_revaluations = fields.Boolean(
        string='Reversable Revaluations',
        help="Revaluations entries will be created "
             "as \"To Be Reversed\".",
        default=True,
    )
