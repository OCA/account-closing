# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Yannick Vaucher, Guewen Baconnier
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

from openerp import models, fields, api
from openerp.exceptions import Warning as UserError
from openerp import _


class WizardCurrencyRevaluation(models.TransientModel):

    _name = 'wizard.currency.revaluation'

    @api.model
    def _get_default_revaluation_date(self):
        """
        Get last date of previous fiscalyear
        """
        current_date = fields.date.today()
        return current_date

    @api.model
    def _get_default_journal_id(self):
        """
        Get default journal if one is defined in company settings
        """
        return self.env.user.company_id.default_currency_reval_journal_id

    revaluation_date = fields.Date(
        string='Revaluation Date',
        required=True,
        default=_get_default_revaluation_date
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal',
        domain="[('type','=','general')]",
        help="You can set the default journal in company settings.",
        required=True,
        default=_get_default_journal_id
    )
    label = fields.Char(
        string='Entry description',
        size=100,
        help="This label will be inserted in entries description. "
             "You can use %(account)s, %(currency)s and %(rate)s keywords.",
        required=True,
        default="%(currency)s %(account)s "
                "%(rate)s currency revaluation"
    )

    @api.model
    def _compute_unrealized_currency_gl(self, currency_id, balances, form):
        """
        Update data dict with the unrealized currency gain and loss
        plus add 'currency_rate' which is the value used for rate in
        computation

        @param int currency_id: currency to revaluate
        @param dict balances: contains foreign balance and balance

        @return: updated data for foreign balance plus rate value used
        """
        context = self.env.context

        currency_obj = self.env['res.currency']

        # Compute unrealized gain loss
        ctx_rate = context.copy()
        ctx_rate['date'] = form.revaluation_date
        cp_currency = form.journal_id.company_id.currency_id

        currency = currency_obj.browse(currency_id)

        foreign_balance = adjusted_balance = balances.get(
            'foreign_balance', 0.0)
        balance = balances.get('balance', 0.0)
        unrealized_gain_loss = 0.0
        if foreign_balance:
            ctx_rate['revaluation'] = True
            adjusted_balance = currency.with_context(ctx_rate).compute(
                foreign_balance, cp_currency
            )
            unrealized_gain_loss = adjusted_balance - balance
            # revaluated_balance =  balance + unrealized_gain_loss
        else:
            if balance:
                if currency_id != cp_currency.id:
                    unrealized_gain_loss = 0.0 - balance
        return {'unrealized_gain_loss': unrealized_gain_loss,
                'currency_rate': currency.rate,
                'revaluated_balance': adjusted_balance}

    @api.model
    def _format_label(self, text, account_id, currency_id, rate):
        """
        Return a text with replaced keywords by values

        @param str text: label template, can use
            %(account)s, %(currency)s, %(rate)s
        @param int account_id: id of the account to display in label
        @param int currency_id: id of the currency to display
        @param float rate: rate to display
        """
        account_obj = self.env['account.account']
        currency_obj = self.env['res.currency']
        account = account_obj.browse(account_id)
        currency = currency_obj.browse(currency_id)
        data = {'account': account.code or False,
                'currency': currency.name or False,
                'rate': rate or False}
        return text % data

    @api.multi
    def _write_adjust_balance(self, account_id, currency_id,
                              partner_id, amount, label, form, sums):
        """
        Generate entries to adjust balance in the revaluation accounts

        @param account_id: ID of account to be reevaluated
        @param amount: Amount to be written to adjust the balance
        @param label: Label to be written on each entry
        @param form: Wizard browse record containing data

        @return: ids of created move_lines
        """

        def create_move_and_lines(amount, debit_account_id, credit_account_id,
                                  sums, analytic_debit_acc_id=False,
                                  analytic_credit_acc_id=False,):

            reversable = form.journal_id.company_id.reversable_revaluations
            base_move = {'name': label,
                         'journal_id': form.journal_id.id,
                         'date': form.revaluation_date,
                         'to_be_reversed': reversable}

            base_line = {'name': label,
                         'partner_id': partner_id,
                         'currency_id': currency_id,
                         'amount_currency': 0.0,
                         'date': form.revaluation_date}

            base_line['gl_foreign_balance'] = sums.get('foreign_balance', 0.0)
            base_line['gl_balance'] = sums.get('balance', 0.0)
            base_line['gl_revaluated_balance'] = sums.get(
                'revaluated_balance', 0.0)
            base_line['gl_currency_rate'] = sums.get('currency_rate', 0.0)

            debit_line = base_line.copy()
            credit_line = base_line.copy()

            debit_line.update({
                'debit': amount,
                'credit': 0.0,
                'account_id': debit_account_id,
            })
            if analytic_debit_acc_id:
                credit_line.update({
                    'analytic_account_id': analytic_debit_acc_id,
                })

            credit_line.update({
                'debit': 0.0,
                'credit': amount,
                'account_id': credit_account_id,
            })
            if analytic_credit_acc_id:
                credit_line.update({
                    'analytic_account_id': analytic_credit_acc_id,
                })
            base_move['line_ids'] = [(0, 0, debit_line), (0, 0, credit_line)]
            created_move = self.env['account.move'].create(base_move)
            created_move.post()
            return [x.id for x in created_move.line_ids]

        if partner_id is None:
            partner_id = False

        company = form.journal_id.company_id or self.env.user.company_id
        created_ids = []
        # over revaluation
        if amount >= 0.01:
            reval_gain_account = company.revaluation_gain_account_id
            if reval_gain_account:

                analytic_acc_id = (company.revaluation_analytic_account_id.id
                                   if company.revaluation_analytic_account_id
                                   else False)

                line_ids = create_move_and_lines(
                    amount, account_id, reval_gain_account.id, sums,
                    analytic_credit_acc_id=analytic_acc_id)

                created_ids.extend(line_ids)

            if company.provision_bs_gain_account_id and \
               company.provision_pl_gain_account_id:

                analytic_acc_id = (
                    company.provision_pl_analytic_account_id and
                    company.provision_pl_analytic_account_id.id or
                    False)

                line_ids = create_move_and_lines(
                    amount, company.provision_bs_gain_account_id.id,
                    company.provision_pl_gain_account_id.id, sums,
                    analytic_credit_acc_id=analytic_acc_id)

                created_ids.extend(line_ids)

        # under revaluation
        elif amount <= -0.01:
            amount = -amount
            reval_loss_account = company.revaluation_loss_account_id
            if reval_loss_account:

                analytic_acc_id = (company.revaluation_analytic_account_id.id
                                   if company.revaluation_analytic_account_id
                                   else False)

                line_ids = create_move_and_lines(
                    amount, reval_loss_account.id, account_id, sums,
                    analytic_debit_acc_id=analytic_acc_id)

                created_ids.extend(line_ids)

            if company.provision_bs_loss_account_id and \
               company.provision_pl_loss_account_id:

                analytic_acc_id = (
                    company.provision_pl_analytic_account_id and
                    company.provision_pl_analytic_account_id.id or
                    False)

                line_ids = create_move_and_lines(
                    amount, company.provision_pl_loss_account_id.id,
                    company.provision_bs_loss_account_id.id, sums,
                    analytic_debit_acc_id=analytic_acc_id)

                created_ids.extend(line_ids)

        return created_ids

    @api.multi
    def revaluate_currency(self):
        """
        Compute unrealized currency gain and loss and add entries to
        adjust balances

        @return: dict to open an Entries view filtered on generated move lines
        """

        account_obj = self.env['account.account']

        company = self.journal_id.company_id or self.env.user.company_id
        if (not company.revaluation_loss_account_id and
            not company.revaluation_gain_account_id and
            not (company.provision_bs_loss_account_id and
                 company.provision_pl_loss_account_id) and
            not (company.provision_bs_gain_account_id and
                 company.provision_pl_gain_account_id)):
            raise Warning(
                _("No revaluation or provision account are defined"
                  " for your company.\n"
                  "You must specify at least one provision account or"
                  " a couple of provision account.")
            )
        created_ids = []
        # Search for accounts Balance Sheet to be revaluated
        # on those criteria
        # - deferral method of account type is not None
        account_ids = account_obj.search([
            ('user_type_id.include_initial_balance', '=', 'True'),
            ('currency_revaluation', '=', True)])

        if not account_ids:
            raise UserError(
                _("No account to be revaluated found. "
                  "Please check 'Allow Currency Revaluation' "
                  "for at least one account in account form.")
            )

        # Get balance sums
        account_sums = account_ids.compute_revaluations(self.revaluation_date)

        for account_id, account_tree in account_sums.iteritems():
            for currency_id, currency_tree in account_tree.iteritems():
                for partner_id, sums in currency_tree.iteritems():
                    if not sums['balance']:
                        continue
                    # Update sums with compute amount currency balance
                    diff_balances = self._compute_unrealized_currency_gl(
                        currency_id,
                        sums, self)
                    account_sums[account_id][currency_id][partner_id].\
                        update(diff_balances)

        # Create entries only after all computation have been done
        for account_id, account_tree in account_sums.iteritems():
            for currency_id, currency_tree in account_tree.iteritems():
                for partner_id, sums in currency_tree.iteritems():
                    adj_balance = sums.get('unrealized_gain_loss', 0.0)
                    if not adj_balance:
                        continue
                    account_type = account_obj.browse(account_id).internal_type
                    if account_type not in ['receivable', 'payable']:
                        partner_id = None
                    rate = sums.get('currency_rate', 0.0)
                    label = self._format_label(
                        self.label, account_id, currency_id, rate
                    )

                    # Write an entry to adjust balance
                    new_ids = self._write_adjust_balance(
                        account_id,
                        currency_id,
                        partner_id,
                        adj_balance,
                        label,
                        self,
                        sums
                    )
                    created_ids.extend(new_ids)

        if created_ids:
            return {'domain': "[('id', 'in', %s)]" % created_ids,
                    'name': _("Created revaluation lines"),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'auto_search': True,
                    'res_model': 'account.move.line',
                    'view_id': False,
                    'search_view_id': False,
                    'type': 'ir.actions.act_window'}
        else:
            raise UserError(
                _("No accounting entry has been posted.")
            )
