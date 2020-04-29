# Copyright 2020 Sergio Corato <https://github.com/sergiocorato>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models, api


class GeneralLedgerReport(models.AbstractModel):
    _inherit = 'report.account_financial_report.general_ledger'

    def _get_initial_balances_bs_ml_domain(self, account_ids,
                                           company_id, date_from,
                                           base_domain, acc_prt=False):
        domain = super()._get_initial_balances_bs_ml_domain(
            account_ids=account_ids, company_id=company_id, date_from=date_from,
            base_domain=base_domain, acc_prt=acc_prt)
        closing_move_ids = self.env['account.move'].search([
            ('closing_type', 'in', ['closing', 'opening', 'loss_profit'])
        ])
        domain += [('move_id', 'not in', closing_move_ids)]
        return domain

    def _get_initial_balances_pl_ml_domain(self, account_ids,
                                           company_id, date_from,
                                           fy_start_date, base_domain):
        domain = super()._get_initial_balances_pl_ml_domain(
            account_ids=account_ids, company_id=company_id, date_from=date_from,
            fy_start_date=fy_start_date, base_domain=base_domain)
        closing_move_ids = self.env['account.move'].search([
            ('closing_type', 'in', ['closing', 'opening', 'loss_profit'])
        ])
        domain += [('move_id', 'not in', closing_move_ids)]
        return domain

    @api.model
    def _get_period_domain(
            self, account_ids, partner_ids, company_id, only_posted_moves,
            date_to, date_from, analytic_tag_ids, cost_center_ids):
        domain = super()._get_period_domain(
            account_ids=account_ids, partner_ids=partner_ids, company_id=company_id,
            only_posted_moves=only_posted_moves, date_to=date_to, date_from=date_from,
            analytic_tag_ids=analytic_tag_ids, cost_center_ids=cost_center_ids)
        closing_move_ids = self.env['account.move'].search([
            ('closing_type', 'in', ['closing', 'opening', 'loss_profit'])
        ])
        domain += [('move_id', 'not in', closing_move_ids)]
        return domain
