# Copyright 2012-2018 Camptocamp SA
# Copyright 2022 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    revaluation_loss_account_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.revaluation_loss_account_id",
        readonly=False,
    )
    revaluation_gain_account_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.revaluation_gain_account_id",
        readonly=False,
    )
    revaluation_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        related="company_id.revaluation_analytic_account_id",
        readonly=False,
    )
    provision_bs_loss_account_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.provision_bs_loss_account_id",
        readonly=False,
    )
    provision_bs_gain_account_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.provision_bs_gain_account_id",
        readonly=False,
    )
    provision_pl_loss_account_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.provision_pl_loss_account_id",
        readonly=False,
    )
    provision_pl_gain_account_id = fields.Many2one(
        comodel_name="account.account",
        related="company_id.provision_pl_gain_account_id",
        readonly=False,
    )
    provision_pl_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        related="company_id.provision_pl_analytic_account_id",
        readonly=False,
    )
    default_currency_reval_journal_id = fields.Many2one(
        comodel_name="account.journal",
        related="company_id.currency_reval_journal_id",
        default_model="res.company",
        readonly=False,
    )
    auto_post_entries = fields.Boolean(
        related="company_id.auto_post_entries",
        readonly=False,
    )
