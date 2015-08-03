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
from openerp.exceptions import Warning
from openerp import _


class WizardCurrencyRevaluation(models.TransientModel):

    _name = 'wizard.currency.revaluation'

    @api.model
    def _get_default_revaluation_date(self):
        """
        Get last date of previous fiscalyear
        """

        fiscalyear_obj = self.env['account.fiscalyear']
        cp = self.env.user.company_id
        # find previous fiscalyear
        current_date = fields.date.today()
        previous_fiscalyear = fiscalyear_obj.search(
            [('date_stop', '<', current_date),
             ('company_id', '=', cp.id)],
            limit=1,
            order='date_start DESC')
        if not previous_fiscalyear:
            return current_date
        return previous_fiscalyear.date_stop

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

    @api.onchange('revaluation_date')
    def on_change_revaluation_date(self):
        revaluation_date = self.revaluation_date
        if not revaluation_date:
            return {}
        move_obj = self.env['account.move']
        company_id = self.env.user.company_id.id
        fiscalyear_obj = self.env['account.fiscalyear']
        fiscalyear = fiscalyear_obj.search(
            [('date_start', '<=', revaluation_date),
             ('date_stop', '>=', revaluation_date),
             ('company_id', '=', company_id)],
            limit=1
        )
        if fiscalyear:
            previous_fiscalyear_ids = fiscalyear_obj.search(
                [('date_stop', '<', fiscalyear.date_start),
                 ('company_id', '=', company_id)],
                limit=1)
            if previous_fiscalyear_ids:
                special_period_ids = [p.id for p in fiscalyear.period_ids
                                      if p.special]
                opening_move_ids = []
                if special_period_ids:
                    opening_move_ids = move_obj.search(
                        [('period_id', '=', special_period_ids[0])])
                if not opening_move_ids or not special_period_ids:
                    raise Warning(
                        _('No opening entries in opening period '
                          'for this fiscal year')
                    )

    @api.model
    def _compute_unrealized_currency_gl(self,
                                        currency_id,
                                        balances,
                                        form):
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

        def create_move():
            reversable = form.journal_id.company_id.reversable_revaluations
            base_move = {'name': label,
                         'journal_id': form.journal_id.id,
                         'period_id': period.id,
                         'date': form.revaluation_date,
                         'to_be_reversed': reversable}
            return move_obj.create(base_move).id

        def create_move_line(line_data, sums):
            base_line = {'name': label,
                         'partner_id': partner_id,
                         'currency_id': currency_id,
                         'amount_currency': 0.0,
                         'date': form.revaluation_date,
                         }
            base_line.update(line_data)
            # we can assume that keys should be equals columns name + gl_
            # but it was not decide when the code was designed. So commented
            # code may sucks:
            # for k, v in sums.items():
            #    line_data['gl_' + k] = v
            base_line['gl_foreign_balance'] = sums.get('foreign_balance', 0.0)
            base_line['gl_balance'] = sums.get('balance', 0.0)
            base_line['gl_revaluated_balance'] = sums.get(
                'revaluated_balance', 0.0)
            base_line['gl_currency_rate'] = sums.get('currency_rate', 0.0)
            return move_line_obj.create(base_line).id
        if partner_id is None:
            partner_id = False
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        period_obj = self.env['account.period']
        company = form.journal_id.company_id or self.env.user.company_id
        period = period_obj.search(
            [('date_start', '<=', form.revaluation_date),
             ('date_stop', '>=', form.revaluation_date),
             ('company_id', '=', company.id),
             ('special', '=', False)],
            limit=1)
        if not period:
            raise Warning(
                _('There is no period for company %s on %s'
                  % (company.name, form.revaluation_date))
            )
        created_ids = []
        # over revaluation
        if amount >= 0.01:
            if company.revaluation_gain_account_id:
                move_id = create_move()
                # Create a move line to Debit account to be revaluated
                line_data = {'debit': amount,
                             'move_id': move_id,
                             'account_id': account_id,
                             }
                created_ids.append(create_move_line(line_data, sums))
                # Create a move line to Credit revaluation gain account
                analytic_acc_id = (company.revaluation_analytic_account_id.id
                                   if company.revaluation_analytic_account_id
                                   else False)
                line_data = {
                    'credit': amount,
                    'account_id': company.revaluation_gain_account_id.id,
                    'move_id': move_id,
                    'analytic_account_id': analytic_acc_id,
                }
                created_ids.append(create_move_line(line_data, sums))
            if company.provision_bs_gain_account_id and \
               company.provision_pl_gain_account_id:
                move_id = create_move()
                analytic_acc_id = (
                    company.provision_pl_analytic_account_id and
                    company.provision_pl_analytic_account_id.id or
                    False)
                # Create a move line to Debit provision BS gain
                line_data = {
                    'debit': amount,
                    'move_id': move_id,
                    'account_id': company.provision_bs_gain_account_id.id, }
                created_ids.append(create_move_line(line_data, sums))
                # Create a move line to Credit provision P&L gain
                line_data = {
                    'credit': amount,
                    'analytic_account_id': analytic_acc_id,
                    'account_id': company.provision_pl_gain_account_id.id,
                    'move_id': move_id, }
                created_ids.append(create_move_line(line_data, sums))

        # under revaluation
        elif amount <= -0.01:
            amount = -amount
            if company.revaluation_loss_account_id:
                move_id = create_move()
                # Create a move line to Debit revaluation loss account
                analytic_acc_id = (company.revaluation_analytic_account_id.id
                                   if company.revaluation_analytic_account_id
                                   else False)
                line_data = {
                    'debit': amount,
                    'move_id': move_id,
                    'account_id': company.revaluation_loss_account_id.id,
                    'analytic_account_id': analytic_acc_id,
                }

                created_ids.append(create_move_line(line_data, sums))
                # Create a move line to Credit account to be revaluated
                line_data = {
                    'credit': amount,
                    'move_id': move_id,
                    'account_id': account_id,
                }
                created_ids.append(create_move_line(line_data, sums))

            if company.provision_bs_loss_account_id and \
               company.provision_pl_loss_account_id:
                move_id = create_move()
                analytic_acc_id = (
                    company.provision_pl_analytic_account_id and
                    company.provision_pl_analytic_account_id.id or
                    False)
                # Create a move line to Debit Provision P&L
                line_data = {
                    'debit': amount,
                    'analytic_account_id': analytic_acc_id,
                    'move_id': move_id,
                    'account_id': company.provision_pl_loss_account_id.id, }
                created_ids.append(create_move_line(line_data, sums))
                # Create a move line to Credit Provision BS
                line_data = {
                    'credit': amount,
                    'move_id': move_id,
                    'account_id': company.provision_bs_loss_account_id.id, }
                created_ids.append(create_move_line(line_data, sums))
        return created_ids

    @api.multi
    def revaluate_currency(self):
        """
        Compute unrealized currency gain and loss and add entries to
        adjust balances

        @return: dict to open an Entries view filtered on generated move lines
        """
        context = self.env.context
        account_obj = self.env['account.account']
        fiscalyear_obj = self.env['account.fiscalyear']
        move_obj = self.env['account.move']
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
        account_ids = account_obj.search(
            [('user_type.close_method', '!=', 'none'),
             ('currency_revaluation', '=', True)])
        if not account_ids:
            raise Warning(
                _("No account to be revaluated found. "
                  "Please check 'Allow Currency Revaluation' "
                  "for at least one account in account form.")
            )
        fiscalyear = fiscalyear_obj.with_context(context).search(
            [('date_start', '<=', self.revaluation_date),
             ('date_stop', '>=', self.revaluation_date),
             ('company_id', '=', company.id)],
            limit=1)
        if not fiscalyear:
            raise Warning(
                _('No fiscalyear found for company %s on %s.' %
                  (company.name, self.revaluation_date))
            )
        special_period_ids = [p.id for p in fiscalyear.period_ids
                              if p.special]
        if not special_period_ids:
            raise Warning(
                _('No special period found for the fiscalyear %s' %
                  fiscalyear.code)
            )
        if special_period_ids:
            opening_move_ids = move_obj.search(
                [('period_id', '=', special_period_ids[0])])
            if not opening_move_ids:
                # if the first move is on this fiscalyear, this is the first
                # financial year
                first_move = move_obj.search(
                    [('company_id', '=', company.id)],
                    order='date', limit=1)
                if not first_move:
                    raise Warning(
                        _('No fiscal entries found')
                    )
                if fiscalyear != first_move.period_id.fiscalyear_id:
                    raise Warning(
                        _('No opening entries in opening period for this '
                          'fiscal year %s' % fiscalyear.code)
                    )
        period_ids = [p.id for p in fiscalyear.period_ids]
        if not period_ids:
            raise Warning(
                _('No period found for the fiscalyear %s' %
                  fiscalyear.code)
            )
        # Get balance sums
        account_sums = account_ids.compute_revaluations(
            period_ids,
            self.revaluation_date)
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
            raise Warning(
                _("No accounting entry has been posted.")
            )
