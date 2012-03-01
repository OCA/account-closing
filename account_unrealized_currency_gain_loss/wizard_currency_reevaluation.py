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

from datetime import date

from osv import osv, fields
from tools.translate import _


class WizardCurrencyReevaluation(osv.osv_memory):
    _name = 'wizard.currency.reevaluation'

    _columns = {'reevaluation_date': fields.date('Reevaluation Date',
                                                 required=True),
                'journal_id': fields.many2one('account.journal',
                                              'Journal',
                                              domain="[('type','=','general')]",
                                              help="You can set the default journal in company settings.",
                                              required=True),
                'currency_type': fields.many2one('res.currency.rate.type',
                                                 'Currency Type',
                                                 help="If no currency_type is selected,"
                                                      " only rates with no type will be browsed.",
                                                 required=False),
                'label': fields.char('Entry description',
                                     size=100,
                                     help="This label will be inserted in entries description."
                                          " You can use %(account)s, %(currency)s and %(rate)s keywords.",
                                     required=True)}

    def _get_default_reevaluation_date(self, cursor, uid, context):
        """
        Get last date of previous period
        """
        context = context or {}

        period_obj = self.pool.get('account.period')
        user_obj = self.pool.get('res.users')
        cp = user_obj.browse(cursor, uid, uid, context=context).company_id
        # find previous period
        current_date = date.today().strftime('%Y-%m-%d')
        previous_period_ids = period_obj.search(cursor, uid,
                                                [('date_stop', '<', current_date),
                                                 ('company_id', '=', cp.id),
                                                 ('special', '=', False)],
                                                limit=1,
                                                order='date_start DESC',
                                                context=context)
        if not previous_period_ids: return current_date
        last_period = period_obj.browse(cursor, uid, previous_period_ids[0], context=context)
        return last_period.date_stop


    def _get_default_journal_id(self, cursor, uid, context):
        """
        Get default journal if one is defined in company settings
        """
        user_obj = self.pool.get('res.users')
        cp = user_obj.browse(cursor, uid, uid, context=context).company_id

        journal = cp.default_currency_reeval_journal_id
        return journal and journal.id or False


    _defaults = {'label': '%(currency)s %(account)s %(rate)s currency reevaluation',
                 'reevaluation_date': _get_default_reevaluation_date,
                 'journal_id': _get_default_journal_id}


    def _compute_unrealized_currency_gl(
            self, cr, uid, account_id, currency_id, data, wiz, context=None):
        """
        Update data dict with the unrealized currency gain and loss
        plus add 'currency_rate' which is the value used for rate in
        computation
        
        @param int account_id: Id of account
        @param dict data: contains foreign balance and balance

        @return: updated data for foreign balance plus rate value used
        """
        context = context or {}
        
        currency_obj = self.pool.get('res.currency')
        rate_obj = self.pool.get('res.currency.rate')

        currency = currency_obj.browse(cr, uid, currency_id, context=context)

        type_id = wiz.currency_type and wiz.currency_type.id or False

        # Get the last rate corresponding to the rate type selected
        # rate name is effective date
        rate_ids = rate_obj.search(cr, uid,
                                   [('currency_rate_type_id', '=', type_id),
                                    ('currency_id', '=', currency_id),
                                    ('name', '<=', wiz.reevaluation_date)],
                                   limit=1,
                                   order='name DESC')

        if not rate_ids:
            if wiz.currency_type:
                raise osv.except_osv(
                    _('Error!'),
                    _("A rate is missing for currency %s. " \
                      "Please add a rate for '%s' type as of %s." %
                      (currency.name,
                       wiz.currency_type.name,
                       wiz.reevaluation_date)))
            else:
                raise osv.except_osv(_('Error!'),
                                     _('No rate found for currency %s.' %
                                      (currency.name,)))

        # Compute unrealized gain loss
        currency_rate = rate_obj.browse(cr, uid, rate_ids[0])
        adj_bal = data[account_id].get('foreign_balance', 0.0) / currency_rate.rate
        balance = data[account_id].get('balance', 0.0)
        data[account_id].update({'unrealized_gain_loss': adj_bal - balance,
                                 'currency_rate': currency_rate.rate})
        return data 

    def _format_label(self, cr, uid, text, account_id, currency,
                      rate, context=None):
        """
        Return a text with replaced keywords by values

        @param str text: label template, can use
            %(account)s, %(currency)s, %(rate)s
        @param int account_id: id of the account to display in label
        @param browse_record currency: browsable record of the
            currency to display
        @param float rate: rate to display
        """
        account_obj = self.pool.get('account.account')
        account_code = account_obj.browse(cr, uid,
                                          account_id,
                                          context=context).code

        data = {'account': account_code or False,
                'currency': currency.name or False,
                'rate': rate or False}
        return text % data

    def _write_adjust_balance(self, cursor, uid, acc_id,
                              cur_id,
                              amount,
                              label,
                              wiz,
                              context=None):
        """
        Generate entries to adjust balance in the reevaluation accounts

        @param acc_id: ID of account to be reevaluated
        @param amount: Amount to be written to adjust the balance
        @param label: Label to be written on each entry
        @param wiz: Wizard browse record containing data

        @return: ids of created move_lines
        """
        context = context or {}

        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        period_obj = self.pool.get('account.period')
        user_obj = self.pool.get('res.users')

        cp = user_obj.browse(cursor, uid, uid).company_id


        period_ids = period_obj.search(cursor, uid,
                                       [('date_start', '<=', wiz.reevaluation_date),
                                        ('date_stop', '>=', wiz.reevaluation_date),
                                        ('company_id','=', cp.id),
                                        ('special', '=', False)],
                                       limit=1,
                                       context=context)

        if not period_ids:
           raise osv.except_osv(_('Error!'),
                                _('There is no period for company %s on %s'
                                  %(cp.name, wiz.reevaluation_date)))

        period = period_obj.browse(cursor, uid, period_ids[0], context=context)

        created_ids = []

        # over reevaluation
        if amount >= 0.01:
            if cp.reevaluation_gain_account_id:
                # Create an entry
                move_data = {'name': label,
                             'journal_id': wiz.journal_id.id,
                             'period_id': period.id,
                             'date': wiz.reevaluation_date,
                             'to_be_reversed': True}
                move_id = move_obj.create(cursor, uid, move_data, context=context)
                # Create a move line to Debit account to be reevaluated
                line_data = {'name': label,
                             'account_id': acc_id,
                             'move_id': move_id,
                             'debit': amount,
                             'currency_id': cur_id,
                             'amount_currency': 0.0,
                             'date': wiz.reevaluation_date}
                created_id = move_line_obj.create(cursor, uid, line_data, context=context)
                created_ids.append(created_id)

                # Create a move line to Credit reevaluation gain account
                line_data = {'name': label,
                             'account_id': cp.reevaluation_gain_account_id.id,
                             'move_id': move_id,
                             'credit': amount,
                             'date': wiz.reevaluation_date}
                created_id = move_line_obj.create(cursor, uid, line_data, context=context)
                created_ids.append(created_id)

            if cp.provision_bs_gain_account_id and \
               cp.provision_pl_gain_account_id:
                 # Create an entry
                move_data = {'name': label,
                             'journal_id': wiz.journal_id.id,
                             'period_id': period.id,
                             'date': wiz.reevaluation_date,
                             'to_be_reversed': True}
                move_id = move_obj.create(cursor, uid, move_data, context=context)

                # Create a move line to Debit provision BS gain
                line_data = {'name': label,
                             'account_id': cp.provision_bs_gain_account_id.id,
                             'move_id': move_id,
                             'debit': amount,
                             'date': wiz.reevaluation_date}
                created_id = move_line_obj.create(cursor, uid, line_data, context=context)
                created_ids.append(created_id)

                # Create a move line to Credit provision P&L gain
                line_data = {'name': label,
                             'account_id': cp.provision_pl_gain_account_id.id,
                             'move_id': move_id,
                             'credit': amount,
                             'date': wiz.reevaluation_date}
                created_id = move_line_obj.create(cursor, uid, line_data, context=context)
                created_ids.append(created_id)


        # under reevaluation
        elif amount <= -0.01:
            amount = -amount
            if cp.reevaluation_loss_account_id:
                # Create an entry
                move_data = {'name': label,
                             'journal_id': wiz.journal_id.id,
                             'period_id': period.id,
                             'date': wiz.reevaluation_date,
                             'to_be_reversed': True}
                move_id = move_obj.create(cursor, uid, move_data, context=context)

                # Create a move line to Debit reevaluation loss account
                line_data = {'name': label,
                             'account_id': cp.reevaluation_loss_account_id.id,
                             'move_id': move_id,
                             'debit': amount,
                             'date': wiz.reevaluation_date}
                created_id = move_line_obj.create(cursor, uid, line_data, context=context)
                created_ids.append(created_id)

                # Create a move line to Credit account to be reevaluated
                line_data = {'name': label,
                             'account_id': acc_id,
                             'move_id': move_id,
                             'credit': amount,
                             'currency_id': cur_id,
                             'amount_currency': 0.0,
                             'date': wiz.reevaluation_date}
                created_id = move_line_obj.create(cursor, uid, line_data, context=context)
                created_ids.append(created_id)

            if cp.provision_bs_loss_account_id and \
               cp.provision_pl_loss_account_id:
                # Create an entry
                move_data = {'name': label,
                             'journal_id': wiz.journal_id.id,
                             'period_id': period.id,
                             'date': wiz.reevaluation_date,
                             'to_be_reversed': True}
                move_id = move_obj.create(cursor, uid, move_data, context=context)

                # Create a move line to Debit Provision P&L
                line_data = {'name': label,
                             'account_id': cp.provision_pl_loss_account_id.id,
                             'move_id': move_id,
                             'debit': amount,
                             'date': wiz.reevaluation_date}
                created_id = move_line_obj.create(cursor, uid, line_data, context=context)
                created_ids.append(created_id)

                # Create a move line to Credit Provision BS
                line_data = {'name': label,
                             'account_id': cp.provision_bs_loss_account_id.id,
                             'move_id': move_id,
                             'credit': amount,
                             'date': wiz.reevaluation_date}
                created_id = move_line_obj.create(cursor, uid, line_data, context=context)
                created_ids.append(created_id)
        return created_ids


    def reevaluate_currency(self, cr, uid, ids, context=None):
        """
        Compute unrealized currency gain and loss and add entries to
        adjust balances

        @return: dict to open an Entries view filtered on generated move lines
        """
        context = context or {}

        user_obj = self.pool.get('res.users')
        account_obj = self.pool.get('account.account')
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        move_obj = self.pool.get('account.move')
        currency_obj = self.pool.get('res.currency')

        cp = user_obj.browse(cr, uid, uid).company_id
        
        if (not cp.reevaluation_loss_account_id and
            not cp.reevaluation_gain_account_id and
            not (cp.provision_bs_loss_account_id and cp.provision_pl_loss_account_id) and
            not (cp.provision_bs_gain_account_id and cp.provision_pl_gain_account_id)):
            raise osv.except_osv(_("Error!"),
                                 _("No reevaluation or provision account are defined"
                                   " for your company.\n"
                                   "You must specify at least one provision account or"
                                   " a couple of provision account."))
        
        created_ids = []
        for wiz in self.browse(cr, uid, ids):

            # Search for accounts Balance Sheet to be reevaluated on those criterions
            # - deferral method of account type is not None
            account_ids = account_obj.search(cr, uid,
                                             [('user_type.close_method', '!=', 'none'),
                                              ('currency_reevaluation', '=', True)])

            if not account_ids:
                raise osv.except_osv(_('Settings Error!'),
                                     _("No account to be reevaluated found. "
                                       "Please check 'Allow Currency Reevaluation' "
                                       "for at least one account in account form."))

            fiscalyear_ids = fiscalyear_obj.search(cr, uid,
                                                   [('date_start', '<=', wiz.reevaluation_date),
                                                    ('date_stop', '>=', wiz.reevaluation_date),
                                                    ('company_id', '=', cp.id)],
                                                   limit=1,
                                                   context=context)

            if not fiscalyear_ids:
                raise osv.except_osv(_('Error!'),
                                     _('No fiscalyear found for company %s on %s.'
                                       %(cp.name, wiz.reevaluation_date))) 

            fiscalyear = fiscalyear_obj.browse(cr, uid, fiscalyear_ids[0], context=context)

            period_ids = [p.id for p in fiscalyear.period_ids if p.special == False]
            if not period_ids:
               raise osv.except_osv(_('Error!'),
                                    _('No period found for the fiscalyear %s' %(fiscalyear.code,)))

            # unless it is the first year check if opening entries have been generated otherwise raise error
            previous_fiscalyear_ids = fiscalyear_obj.search(cr, uid,
                                                        [('date_stop', '<', fiscalyear.date_start),
                                                         ('company_id', '=', cp.id)],
                                                        limit=1,
                                                        context=context)            
            if previous_fiscalyear_ids:
                special_period_ids = [p.id for p in fiscalyear.period_ids if p.special == True]
                if not special_period_ids:
                    raise osv.except_osv(_('Error!'),
                                         _('No openning opening period found for this fiscal year.'))
            
             
                opening_move_ids = move_obj.search(cr, uid,
                                                   [('period_id', '=', special_period_ids[0])])
                if not opening_move_ids:
                    raise osv.except_osv(_('Error!'),
                                         _('You must generate an opening entry'
                                           ' in opening period for this fiscal year.'))

            
            currency_ids = currency_obj.search(cr, uid, [])
            currencies = currency_obj.browse(
                cr, uid, currency_ids, context=context)
            for currency in currencies:
                # Filter move lines based on user choices
                filters = ("l.date <= '%s'"
                           " AND l.period_id IN %s"
                           " AND l.currency_id = %s" %
                            (wiz.reevaluation_date,
                             str(tuple(period_ids)),
                             currency.id))
                # Get balance sums
                sums = account_obj.compute_balances(cr, uid,
                                                    account_ids,
                                                    context=context,
                                                    query=filters)

                for acc_id in account_ids:
                    if sums[acc_id]['balance']:
                        # Update sums with compute amount currency balance
                        self._compute_unrealized_currency_gl(
                            cr, uid, acc_id, currency.id,
                            sums, wiz, context=context)
    
                # Create entries only after all computation have been done
                for acc_id in account_ids:
                    adj_balance = sums[acc_id].get('unrealized_gain_loss', 0.0)
                    if adj_balance:
                        
                        rate = sums[acc_id].get('currency_rate', 0.0)
                        
                        label = self._format_label(
                            cr, uid, wiz.label, acc_id, currency, rate)
                        # Write an entry to adjust balance
                        new_ids = self._write_adjust_balance(
                            cr, uid, acc_id, currency.id,
                            adj_balance, label, wiz, context=context)
                        created_ids.extend(new_ids)
           
        if created_ids:
            return {'domain': "[('id','in', %s)]" %(created_ids,),
                    'name': _("Created reevaluation lines"),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'auto_search': True,
                    'res_model': 'account.move.line',
                    'view_id': False,
                    'search_view_id': False,
                    'type': 'ir.actions.act_window'}
        else:
            raise osv.except_osv(_("Warning"), _("No accounting entry have been posted."))  

WizardCurrencyReevaluation()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
