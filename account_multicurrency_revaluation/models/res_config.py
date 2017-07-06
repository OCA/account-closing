# -*- coding: utf-8 -*-
# Copyright 2012-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, fields, api


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    revaluation_loss_account_id = fields.Many2one(
        related='company_id.revaluation_loss_account_id',
        comodel_name='account.account',
        string='Revaluation loss account *',
        domain=[('internal_type', '=', 'other')],
    )
    revaluation_gain_account_id = fields.Many2one(
        related='company_id.revaluation_gain_account_id',
        comodel_name='account.account',
        string='Revaluation gain account *',
        domain=[('internal_type', '=', 'other')],
    )
    revaluation_analytic_account_id = fields.Many2one(
        related='company_id.revaluation_analytic_account_id',
        comodel_name='account.analytic.account',
        string='Revaluation Analytic account *'
    )
    provision_bs_loss_account_id = fields.Many2one(
        related='company_id.provision_bs_loss_account_id',
        comodel_name='account.account',
        string='Provision B.S. loss account *',
        domain=[('internal_type', '=', 'other')]
    )
    provision_bs_gain_account_id = fields.Many2one(
        related='company_id.provision_bs_gain_account_id',
        comodel_name='account.account',
        string='Provision B.S. gain account *',
        domain=[('internal_type', '=', 'other')]
    )
    provision_pl_loss_account_id = fields.Many2one(
        related='company_id.provision_pl_loss_account_id',
        comodel_name='account.account',
        string='Provision P&L loss account *',
        domain=[('internal_type', '=', 'other')]
    )
    provision_pl_gain_account_id = fields.Many2one(
        related='company_id.provision_pl_gain_account_id',
        comodel_name='account.account',
        string='Provision P&L gain account *',
        domain=[('internal_type', '=', 'other')]
    )
    provision_pl_analytic_account_id = fields.Many2one(
        related='company_id.provision_pl_analytic_account_id',
        comodel_name='account.analytic.account',
        string='Provision P&L Analytic account *'
    )
    default_currency_reval_journal_id = fields.Many2one(
        related='company_id.default_currency_reval_journal_id',
        comodel_name='account.journal',
        string='Currency gain & loss Default Journal *',
        domain=[('type', '=', 'general')]
    )
    reversable_revaluations = fields.Boolean(
        related='company_id.reversable_revaluations',
        string='Reversable Revaluations *',
        help="Revaluations entries will be created "
             "as \"To Be Reversed\".",
        default=True,
    )

    @api.multi
    def onchange_company_id(self, company_id):
        res = super(AccountConfigSettings, self
                    ).onchange_company_id(company_id)
        company = self.env['res.company'].browse(company_id)
        res['value']['revaluation_loss_account_id'] = (
            company.revaluation_loss_account_id.id)
        res['value']['revaluation_gain_account_id'] = (
            company.revaluation_gain_account_id.id)
        res['value']['revaluation_analytic_account_id'] = (
            company.revaluation_analytic_account_id.id)
        res['value']['provision_bs_loss_account_id'] = (
            company.provision_bs_loss_account_id.id)
        res['value']['provision_bs_gain_account_id'] = (
            company.provision_bs_gain_account_id.id)
        res['value']['provision_pl_loss_account_id'] = (
            company.provision_pl_loss_account_id.id)
        res['value']['provision_pl_gain_account_id'] = (
            company.provision_pl_gain_account_id.id)
        res['value']['provision_pl_analytic_account_id'] = (
            company.provision_pl_analytic_account_id.id)
        res['value']['default_currency_reval_journal_id'] = (
            company.default_currency_reval_journal_id.id)
        res['value']['reversable_revaluations'] = (
            company.reversable_revaluations.id)
        return res
