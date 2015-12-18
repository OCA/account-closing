# -*- encoding: utf-8 -*-
##############################################################################
#
#    Account Cut-off Base module for OpenERP
#    Copyright (C) 2013 Akretion (http://www.akretion.com)
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
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

from openerp.osv import orm, fields
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from datetime import datetime


class account_cutoff(orm.Model):
    _name = 'account.cutoff'
    _rec_name = 'cutoff_date'
    _order = 'cutoff_date desc'
    _inherit = ['mail.thread']
    _description = 'Account Cut-off'
    _track = {
        'state': {
            'account_cutoff_base.cutoff_done':
            lambda self, cr, uid, obj, ctx=None: obj['state'] == 'done',
        }
    }

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default.update({
            'cutoff_date': '%d-12-31' % datetime.today().year,
            'move_id': False,
            'state': 'draft',
            'line_ids': False,
        })
        return super(account_cutoff, self).copy(
            cr, uid, id, default=default, context=context)

    def _compute_total_cutoff(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for cutoff in self.browse(cr, uid, ids, context=context):
            res[cutoff.id] = 0
            for line in cutoff.line_ids:
                res[cutoff.id] += line.cutoff_amount
        return res

    _columns = {
        'cutoff_date': fields.date(
            'Cut-off Date', required=True, readonly=True,
            states={'draft': [('readonly', False)]},
            track_visibility='always'),
        'type': fields.selection([
            ('accrued_revenue', 'Accrued Revenue'),
            ('accrued_expense', 'Accrued Expense'),
            ('prepaid_revenue', 'Prepaid Revenue'),
            ('prepaid_expense', 'Prepaid Expense'),
        ], 'Type', required=True, readonly=True,
            states={'draft': [('readonly', False)]}),
        'move_id': fields.many2one(
            'account.move', 'Cut-off Journal Entry', readonly=True),
        'move_label': fields.char(
            'Label of the Cut-off Journal Entry',
            size=64, required=True, readonly=True,
            states={'draft': [('readonly', False)]},
            help="This label will be written in the 'Name' field of the "
            "Cut-off Account Move Lines and in the 'Reference' field of "
            "the Cut-off Account Move."),
        'cutoff_account_id': fields.many2one(
            'account.account', 'Cut-off Account',
            domain=[('type', '<>', 'view'), ('type', '<>', 'closed')],
            required=True, readonly=True,
            states={'draft': [('readonly', False)]}),
        'cutoff_journal_id': fields.many2one(
            'account.journal', 'Cut-off Account Journal', required=True,
            readonly=True, states={'draft': [('readonly', False)]}),
        'total_cutoff_amount': fields.function(
            _compute_total_cutoff, type='float', string="Total Cut-off Amount",
            readonly=True, track_visibility='always'),
        'company_id': fields.many2one(
            'res.company', 'Company', required=True, readonly=True,
            states={'draft': [('readonly', False)]}),
        'company_currency_id': fields.related(
            'company_id', 'currency_id', readonly=True, type='many2one',
            relation='res.currency', string='Company Currency'),
        'line_ids': fields.one2many(
            'account.cutoff.line', 'parent_id', 'Cut-off Lines', readonly=True,
            states={'draft': [('readonly', False)]}),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('done', 'Done'),
        ],
            'State', select=True, readonly=True, track_visibility='onchange',
            help="State of the cutoff. When the Journal Entry is created, "
            "the state is set to 'Done' and the fields become read-only."),
    }

    def _get_default_journal(self, cr, uid, context=None):
        cur_user = self.pool['res.users'].browse(cr, uid, uid, context=context)
        return cur_user.company_id.default_cutoff_journal_id.id or None

    def _default_move_label(self, cr, uid, context=None):
        if context is None:
            context = {}
        type = context.get('type')
        cutoff_date = context.get('cutoff_date')
        if cutoff_date:
            cutoff_date_label = ' dated %s' % cutoff_date
        else:
            cutoff_date_label = ''
        label = ''
        if type == 'accrued_expense':
            label = _('Accrued Expense%s') % cutoff_date_label
        elif type == 'accrued_revenue':
            label = _('Accrued Revenue%s') % cutoff_date_label
        elif type == 'prepaid_revenue':
            label = _('Prepaid Revenue%s') % cutoff_date_label
        elif type == 'prepaid_expense':
            label = _('Prepaid Expense%s') % cutoff_date_label
        return label

    def _default_type(self, cr, uid, context=None):
        if context is None:
            context = {}
        return context.get('type')

    def _inherit_default_cutoff_account_id(self, cr, uid, context=None):
        '''Function designed to be inherited by other cutoff modules'''
        return None

    def _default_cutoff_account_id(self, cr, uid, context=None):
        '''This function can't be inherited, so we use a second function'''
        return self._inherit_default_cutoff_account_id(
            cr, uid, context=context)

    _defaults = {
        'state': 'draft',
        'company_id': lambda self, cr, uid, context:
        self.pool['res.users'].browse(
            cr, uid, uid, context=context).company_id.id,
        'cutoff_journal_id': lambda self, cr, uid, context: self.
            _get_default_journal(cr, uid, context=context),
        'move_label': _default_move_label,
        'type': _default_type,
        'cutoff_account_id': _default_cutoff_account_id,
    }

    _sql_constraints = [(
        'date_type_company_uniq',
        'unique(cutoff_date, company_id, type)',
        'A cutoff of the same type already exists with this cut-off date !'
    )]

    def cutoff_date_onchange(
            self, cr, uid, ids, type, cutoff_date, move_label, context=None):
        if context is None:
            context = {}
        res = {'value': {}}
        if type and cutoff_date:
            ctx = context.copy()
            ctx.update({'type': type, 'cutoff_date': cutoff_date})
            res['value']['move_label'] = self._default_move_label(
                cr, uid, context=ctx)
        return res

    def back2draft(self, cr, uid, ids, context=None):
        assert len(ids) == 1,\
            'This function should only be used for a single id at a time'
        cur_cutoff = self.browse(cr, uid, ids[0], context=context)
        if cur_cutoff.move_id:
            self.pool['account.move'].unlink(
                cr, uid, [cur_cutoff.move_id.id], context=context)
        self.write(cr, uid, ids[0], {'state': 'draft'}, context=context)
        return True

    def _prepare_move(self, cr, uid, cur_cutoff, to_provision, context=None):
        if context is None:
            context = {}
        movelines_to_create = []
        amount_total = 0
        move_label = cur_cutoff.move_label
        merge_keys = self._get_merge_keys()
        for merge_values, amount in to_provision.items():
            vals = {
                'name': move_label,
                'debit': amount < 0 and amount * -1 or 0,
                'credit': amount >= 0 and amount or 0,
            }
            for k, v in zip(merge_keys, merge_values):
                vals[k] = v
            movelines_to_create.append((0, 0, vals))
            amount_total += amount

        # add contre-partie
        counterpart_amount = amount_total * -1
        movelines_to_create.append((0, 0, {
            'account_id': cur_cutoff.cutoff_account_id.id,
            'debit': counterpart_amount < 0 and counterpart_amount * -1 or 0,
            'credit': counterpart_amount >= 0 and counterpart_amount or 0,
            'name': move_label,
            'analytic_account_id': False,
        }))

        # Select period
        local_ctx = context.copy()
        local_ctx['account_period_prefer_normal'] = True
        period_search = self.pool['account.period'].find(
            cr, uid, cur_cutoff.cutoff_date, context=local_ctx)
        if len(period_search) != 1:
            raise orm.except_orm(
                'Error:', "No matching period for date '%s'"
                % cur_cutoff.cutoff_date)
        period_id = period_search[0]

        res = {
            'journal_id': cur_cutoff.cutoff_journal_id.id,
            'date': cur_cutoff.cutoff_date,
            'period_id': period_id,
            'ref': move_label,
            'to_be_reversed': True,
            'line_id': movelines_to_create,
        }
        return res

    def _prepare_provision_line(self, cr, uid, cutoff_line,
                                context=None):
        """ Convert a cutoff line to elements of a move line

        The returned dictionary must at least contain 'account_id'
        and 'amount' (< 0 means debit).

        If you ovverride this, the added fields must also be
        added in an override of _get_merge_keys.
        """
        return {
            'account_id': cutoff_line.cutoff_account_id.id,
            'analytic_account_id': cutoff_line.analytic_account_id.id,
            'amount': cutoff_line.cutoff_amount,
        }

    def _prepare_provision_tax_line(self, cr, uid, cutoff_tax_line,
                                    context=None):
        """ Convert a cutoff tax line to elements of a move line

        See _prepare_provision_line for more info.
        """
        return {
            'account_id': cutoff_tax_line.cutoff_account_id.id,
            'analytic_account_id': cutoff_tax_line.analytic_account_id.id,
            'amount': cutoff_tax_line.cutoff_amount,
        }

    def _get_merge_keys(self):
        """ Return merge criteria for provision lines

        The returned list must contain valid field names
        for account.move.line. Provision lines with the
        same values for these fields will be merged.
        The list must at least contain account_id.
        """
        return ['account_id', 'analytic_account_id']

    def _merge_provision_lines(self, cr, uid, provision_lines, context=None):
        """ merge provision line

        Returns a dictionary {key, amount} where key is
        a tuple containing the values of the properties in _get_merge_keys()
        """
        to_provision = {}
        merge_keys = self._get_merge_keys()
        for provision_line in provision_lines:
            key = tuple([provision_line.get(key) for key in merge_keys])
            if key in to_provision:
                to_provision[key] += provision_line['amount']
            else:
                to_provision[key] = provision_line['amount']
        return to_provision

    def create_move(self, cr, uid, ids, context=None):
        assert len(ids) == 1, \
            'This function should only be used for a single id at a time'
        move_obj = self.pool['account.move']
        cur_cutoff = self.browse(cr, uid, ids[0], context=context)
        if cur_cutoff.move_id:
            raise orm.except_orm(
                _('Error:'),
                _("The Cut-off Journal Entry already exists. You should "
                    "delete it before running this function."))
        if not cur_cutoff.line_ids:
            raise orm.except_orm(
                _('Error:'),
                _("There are no lines on this Cut-off, so we can't create "
                    "a Journal Entry."))
        provision_lines = []
        for line in cur_cutoff.line_ids:
            provision_lines.append(
                self._prepare_provision_line(
                    cr, uid, line, context=context))
            for tax_line in line.tax_line_ids:
                provision_lines.append(
                    self._prepare_provision_tax_line(
                        cr, uid, tax_line, context=context))
        to_provision = self._merge_provision_lines(
            cr, uid, provision_lines, context=context)
        vals = self._prepare_move(
            cr, uid, cur_cutoff, to_provision, context=context)
        move_id = move_obj.create(cr, uid, vals, context=context)
        move_obj.validate(cr, uid, [move_id], context=context)
        self.write(cr, uid, ids[0], {
            'move_id': move_id,
            'state': 'done',
        }, context=context)

        action = {
            'name': 'Cut-off Account Move',
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_id': move_id,
            'view_id': False,
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'nodestroy': False,
            'target': 'current',
        }
        return action


class account_cutoff_line(orm.Model):
    _name = 'account.cutoff.line'
    _description = 'Account Cut-off Line'

    _columns = {
        'parent_id': fields.many2one(
            'account.cutoff', 'Cut-off', ondelete='cascade'),
        'name': fields.char('Description', size=64),
        'company_currency_id': fields.related(
            'parent_id', 'company_currency_id', type='many2one',
            relation='res.currency', string="Company Currency", readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'account_id': fields.many2one(
            'account.account', 'Account',
            domain=[('type', '<>', 'view'), ('type', '<>', 'closed')],
            required=True, readonly=True),
        'cutoff_account_id': fields.many2one(
            'account.account', 'Cut-off Account',
            domain=[('type', '<>', 'view'), ('type', '<>', 'closed')],
            required=True, readonly=True),
        'cutoff_account_code': fields.related(
            'cutoff_account_id', 'code', type='char',
            string='Cut-off Account Code', readonly=True),
        'analytic_account_id': fields.many2one(
            'account.analytic.account', 'Analytic Account',
            domain=[('type', 'not in', ('view', 'template'))],
            readonly=True),
        'analytic_account_code': fields.related(
            'analytic_account_id', 'code', type='char',
            string='Analytic Account Code', readonly=True),
        'currency_id': fields.many2one(
            'res.currency', 'Amount Currency', readonly=True,
            help="Currency of the 'Amount' field."),
        'amount': fields.float(
            'Amount', digits_compute=dp.get_precision('Account'),
            readonly=True,
            help="Amount that is used as base to compute the Cut-off Amount. "
            "This Amount is in the 'Amount Currency', which may be different "
            "from the 'Company Currency'."),
        'cutoff_amount': fields.float(
            'Cut-off Amount', digits_compute=dp.get_precision('Account'),
            readonly=True,
            help="Cut-off Amount without taxes in the Company Currency."),
        'tax_ids': fields.many2many(
            'account.tax', id1='cutoff_line_id', id2='tax_id', string='Taxes',
            readonly=True),
        'tax_line_ids': fields.one2many(
            'account.cutoff.tax.line', 'parent_id', 'Cut-off Tax Lines',
            readonly=True),
    }


class account_cutoff_tax_line(orm.Model):
    _name = 'account.cutoff.tax.line'
    _description = 'Account Cut-off Tax Line'

    _columns = {
        'parent_id': fields.many2one(
            'account.cutoff.line', 'Account Cut-off Line',
            ondelete='cascade', required=True),
        'tax_id': fields.many2one('account.tax', 'Tax', required=True),
        'cutoff_account_id': fields.many2one(
            'account.account', 'Cut-off Account',
            domain=[('type', '<>', 'view'), ('type', '<>', 'closed')],
            required=True, readonly=True),
        'analytic_account_id': fields.many2one(
            'account.analytic.account', 'Analytic Account',
            domain=[('type', 'not in', ('view', 'template'))],
            readonly=True),
        'base': fields.float(
            'Base', digits_compute=dp.get_precision('Account'),
            readonly=True, help="Base Amount in the currency of the PO."),
        'amount': fields.float(
            'Tax Amount', digits_compute=dp.get_precision('Account'),
            readonly=True, help='Tax Amount in the currency of the PO.'),
        'sequence': fields.integer('Sequence', readonly=True),
        'cutoff_amount': fields.float(
            'Cut-off Tax Amount', digits_compute=dp.get_precision('Account'),
            readonly=True,
            help="Tax Cut-off Amount in the company currency."),
        'currency_id': fields.related(
            'parent_id', 'currency_id', type='many2one',
            relation='res.currency', string='Currency', readonly=True),
        'company_currency_id': fields.related(
            'parent_id', 'company_currency_id',
            type='many2one', relation='res.currency',
            string="Company Currency", readonly=True),
    }


class account_cutoff_mapping(orm.Model):
    _name = 'account.cutoff.mapping'
    _description = 'Account Cut-off Mapping'
    _rec_name = 'account_id'

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'account_id': fields.many2one(
            'account.account', 'Regular Account',
            domain=[('type', '<>', 'view'), ('type', '<>', 'closed')],
            required=True),
        'cutoff_account_id': fields.many2one(
            'account.account', 'Cut-off Account',
            domain=[('type', '<>', 'view'), ('type', '<>', 'closed')],
            required=True),
        'cutoff_type': fields.selection([
            ('all', 'All Cut-off Types'),
            ('accrued_revenue', 'Accrued Revenue'),
            ('accrued_expense', 'Accrued Expense'),
            ('prepaid_revenue', 'Prepaid Revenue'),
            ('prepaid_expense', 'Prepaid Expense'),
        ], 'Cut-off Type', required=True),
    }

    _defaults = {
        'company_id': lambda self, cr, uid, context:
        self.pool['res.users'].browse(
            cr, uid, uid, context=context).company_id.id,
    }

    def _get_mapping_dict(
            self, cr, uid, company_id, cutoff_type='all', context=None):
        '''return a dict with:
        key = ID of account,
        value = ID of cutoff_account'''
        if cutoff_type == 'all':
            cutoff_type_filter = ('all')
        else:
            cutoff_type_filter = ('all', cutoff_type)
        mapping_ids = self.search(
            cr, uid, [
                ('company_id', '=', company_id),
                ('cutoff_type', 'in', cutoff_type_filter),
            ],
            context=context)
        mapping_read = self.read(cr, uid, mapping_ids, context=context)
        mapping = {}
        for item in mapping_read:
            mapping[item['account_id'][0]] = item['cutoff_account_id'][0]
        return mapping
