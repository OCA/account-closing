# Copyright 2012-2018 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    revaluation_loss_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Revaluation loss account",
        domain=[("internal_type", "=", "other")],
    )
    revaluation_gain_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Revaluation gain account",
        domain=[("internal_type", "=", "other")],
    )
    revaluation_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account", string="Revaluation Analytic account"
    )
    provision_bs_loss_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Provision B.S. loss account",
        domain=[("internal_type", "=", "other")],
    )
    provision_bs_gain_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Provision B.S. gain account",
        domain=[("internal_type", "=", "other")],
    )
    provision_pl_loss_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Provision P&L loss account",
        domain=[("internal_type", "=", "other")],
    )
    provision_pl_gain_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Provision P&L gain account",
        domain=[("internal_type", "=", "other")],
    )
    provision_pl_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account", string="Provision P&L Analytic account"
    )
    currency_reval_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Currency gain & loss Default Journal",
        domain=[("type", "=", "general")],
    )
    reversable_revaluations = fields.Boolean(
        string="Reversable Revaluations",
        help="Revaluations entries will be created " 'as "To Be Reversed".',
        default=True,
    )
