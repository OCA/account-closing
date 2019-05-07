# Copyright 2013-2016 Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountCutoff(models.Model):
    _name = 'account.cutoff'
    _rec_name = 'cutoff_date'
    _order = 'cutoff_date desc'
    _inherit = ['mail.thread']
    _description = 'Account Cut-off'

    @api.depends('line_ids', 'line_ids.cutoff_amount')
    def _compute_total_cutoff(self):
        res = self.env['account.cutoff.line'].read_group(
            [('parent_id', 'in', self.ids)],
            ['parent_id', 'cutoff_amount'],
            ['parent_id'])
        for re in res:
            cutoff = self.browse(re['parent_id'][0])
            cutoff.total_cutoff_amount = re['cutoff_amount']

    @property
    def cutoff_type_label_map(self):
        return {
            'accrued_expense': _('Accrued Expense'),
            'accrued_revenue': _('Accrued Revenue'),
            'prepaid_revenue': _('Prepaid Revenue'),
            'prepaid_expense': _('Prepaid Expense'),
        }

    @api.model
    def _default_move_label(self):
        cutoff_type = self.env.context.get('cutoff_type')
        label = self.cutoff_type_label_map.get(cutoff_type, '')
        return label

    def _selection_cutoff_type(self):
        # generate cutoff types from mapping
        return list(self.cutoff_type_label_map.items())

    @api.model
    def _default_cutoff_account_id(self):
        """Default account must always be None"""
        return None

    @api.model
    def _default_cutoff_journal_id(self):
        return self.env.user.company_id.default_cutoff_journal_id

    cutoff_date = fields.Date(
        string='Cut-off Date', readonly=True,
        states={'draft': [('readonly', False)]}, copy=False,
        track_visibility='onchange'
    )
    cutoff_type = fields.Selection(
        selection='_selection_cutoff_type',
        string='Type',
        required=True,
        readonly=True,
        default=lambda self: self.env.context.get('cutoff_type'),
        states={'draft': [('readonly', False)]},
        oldname='type'
    )
    move_id = fields.Many2one(
        'account.move',
        string='Cut-off Journal Entry',
        readonly=True,
        copy=False
    )
    move_label = fields.Char(
        string='Label of the Cut-off Journal Entry',
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self._default_move_label(),
        help="This label will be written in the 'Name' field of the "
        "Cut-off Account Move Lines and in the 'Reference' field of "
        "the Cut-off Account Move."
    )
    cutoff_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Cut-off Account',
        domain=[('deprecated', '=', False)],
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self._default_cutoff_account_id()
    )
    cutoff_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Cut-off Account Journal',
        default=lambda self: self._default_cutoff_journal_id(),
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    total_cutoff_amount = fields.Monetary(
        compute='_compute_total_cutoff',
        string="Total Cut-off Amount",
        currency_field='company_currency_id',
        readonly=True, track_visibility='onchange'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: self.env['res.company']._company_default_get(
            'account.cutoff')
    )
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Company Currency'
    )
    line_ids = fields.One2many(
        comodel_name='account.cutoff.line',
        inverse_name='parent_id',
        string='Cut-off Lines',
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('done', 'Done')],
        index=True,
        readonly=True,
        track_visibility='onchange',
        default='draft',
        copy=False,
        help="State of the cutoff. When the Journal Entry is created, "
        "the state is set to 'Done' and the fields become read-only."
    )

    _sql_constraints = [(
        'date_type_company_uniq',
        'unique(cutoff_date, company_id, cutoff_type)',
        _('A cutoff of the same type already exists with this cut-off date !')
        )]

    def back2draft(self):
        self.ensure_one()
        if self.move_id:
            self.move_id.unlink()
        self.state = 'draft'

    def _get_merge_keys(self):
        """ Return merge criteria for provision lines

        The returned list must contain valid field names
        for account.move.line. Provision lines with the
        same values for these fields will be merged.
        The list must at least contain account_id.
        """
        return ['account_id', 'analytic_account_id']

    def _prepare_move(self, to_provision):
        self.ensure_one()
        movelines_to_create = []
        amount_total = 0
        move_label = self.move_label
        merge_keys = self._get_merge_keys()
        for merge_values, amount in to_provision.items():
            amount = self.company_currency_id.round(amount)
            vals = {
                'name': move_label,
                'debit': amount < 0 and amount * -1 or 0,
                'credit': amount >= 0 and amount or 0,
            }
            for k, v in zip(merge_keys, merge_values):
                vals[k] = v
            movelines_to_create.append((0, 0, vals))
            amount_total += amount

        # add counter-part
        counterpart_amount = self.company_currency_id.round(
            amount_total * -1)
        movelines_to_create.append((0, 0, {
            'account_id': self.cutoff_account_id.id,
            'name': move_label,
            'debit': counterpart_amount < 0 and counterpart_amount * -1 or 0,
            'credit': counterpart_amount >= 0 and counterpart_amount or 0,
            'analytic_account_id': False,
        }))

        res = {
            'journal_id': self.cutoff_journal_id.id,
            'date': self.cutoff_date,
            'ref': move_label,
            'line_ids': movelines_to_create,
        }
        return res

    def _prepare_provision_line(self, cutoff_line):
        """ Convert a cutoff line to elements of a move line.

        The returned dictionary must at least contain 'account_id'
        and 'amount' (< 0 means debit).

        If you override this, the added fields must also be
        added in an override of _get_merge_keys.
        """
        return {
            'account_id': cutoff_line.cutoff_account_id.id,
            'analytic_account_id': cutoff_line.analytic_account_id.id,
            'amount': cutoff_line.cutoff_amount,
        }

    def _prepare_provision_tax_line(self, cutoff_tax_line):
        """ Convert a cutoff tax line to elements of a move line.

        See _prepare_provision_line for more info.
        """
        return {
            'account_id': cutoff_tax_line.cutoff_account_id.id,
            'analytic_account_id': cutoff_tax_line.analytic_account_id.id,
            'amount': cutoff_tax_line.cutoff_amount,
        }

    def _merge_provision_lines(self, provision_lines):
        """ Merge provision line.

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

    def create_move(self):
        self.ensure_one()
        move_obj = self.env['account.move']
        if self.move_id:
            raise UserError(_(
                "The Cut-off Journal Entry already exists. You should "
                "delete it before running this function."))
        if not self.line_ids:
            raise UserError(_(
                "There are no lines on this Cut-off, so we can't create "
                "a Journal Entry."))
        provision_lines = []
        for line in self.line_ids:
            provision_lines.append(
                self._prepare_provision_line(line))
            for tax_line in line.tax_line_ids:
                provision_lines.append(
                    self._prepare_provision_tax_line(tax_line))
        to_provision = self._merge_provision_lines(provision_lines)
        vals = self._prepare_move(to_provision)
        move = move_obj.create(vals)
        self.write({'move_id': move.id, 'state': 'done'})

        action = self.env['ir.actions.act_window'].for_xml_id(
            'account', 'action_move_journal_line')
        action.update({
            'view_mode': 'form,tree',
            'res_id': move.id,
            'view_id': False,
            'views': False,
        })
        return action

    def get_lines(self):
        """This method is designed to be inherited in other modules"""
        self.ensure_one()
        # Delete existing lines
        self.line_ids.unlink()
        return True

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_(
                    "You cannot delete cutoff records that are not "
                    "in draft state."))
        return super(AccountCutoff, self).unlink()

    def button_line_tree(self):
        action = self.env['ir.actions.act_window'].for_xml_id(
            'account_cutoff_base', 'account_cutoff_line_action')
        action.update({
            'domain': [('parent_id', '=', self.id)],
            'views': False,
            'context': self._context,
            })
        return action


class AccountCutoffLine(models.Model):
    _name = 'account.cutoff.line'
    _description = 'Account Cut-off Line'

    parent_id = fields.Many2one(
        'account.cutoff', string='Cut-off', ondelete='cascade')
    name = fields.Char('Description')
    company_currency_id = fields.Many2one(
        related='parent_id.company_currency_id',
        string="Company Currency")
    partner_id = fields.Many2one(
        'res.partner', string='Partner', readonly=True)
    account_id = fields.Many2one(
        'account.account', 'Account',
        domain=[('deprecated', '=', False)], required=True, readonly=True)
    cutoff_account_id = fields.Many2one(
        'account.account', string='Cut-off Account',
        domain=[('deprecated', '=', False)], required=True, readonly=True)
    cutoff_account_code = fields.Char(
        related='cutoff_account_id.code',
        string='Cut-off Account Code', readonly=True)
    analytic_account_id = fields.Many2one(
        'account.analytic.account', string='Analytic Account',
        domain=[('account_type', '!=', 'closed')], readonly=True)
    analytic_account_code = fields.Char(
        related='analytic_account_id.code')
    currency_id = fields.Many2one(
        'res.currency', string='Amount Currency', readonly=True,
        help="Currency of the 'Amount' field.")
    amount = fields.Monetary(
        currency_field='currency_id', readonly=True,
        help="Amount that is used as base to compute the Cut-off Amount. "
        "This Amount is in the 'Amount Currency', which may be different "
        "from the 'Company Currency'.")
    cutoff_amount = fields.Monetary(
        string='Cut-off Amount', currency_field='company_currency_id',
        readonly=True,
        help="Cut-off Amount without taxes in the Company Currency.")
    tax_ids = fields.Many2many(
        'account.tax', column1='cutoff_line_id', column2='tax_id',
        string='Taxes', readonly=True)
    tax_line_ids = fields.One2many(
        'account.cutoff.tax.line', 'parent_id', string='Cut-off Tax Lines',
        readonly=True)


class AccountCutoffTaxLine(models.Model):
    _name = 'account.cutoff.tax.line'
    _description = 'Account Cut-off Tax Line'

    parent_id = fields.Many2one(
        'account.cutoff.line', string='Account Cut-off Line',
        ondelete='cascade', required=True)
    tax_id = fields.Many2one('account.tax', string='Tax', required=True)
    cutoff_account_id = fields.Many2one(
        'account.account', string='Cut-off Account',
        domain=[('deprecated', '=', False)], required=True, readonly=True)
    analytic_account_id = fields.Many2one(
        'account.analytic.account', string='Analytic Account',
        domain=[('account_type', '!=', 'closed')], readonly=True)
    base = fields.Monetary(
        currency_field='currency_id',
        readonly=True, help="Base Amount in the currency of the PO.")
    amount = fields.Monetary(
        string='Tax Amount', currency_field='currency_id',
        readonly=True, help='Tax Amount in the currency of the PO.')
    sequence = fields.Integer(readonly=True)
    cutoff_amount = fields.Monetary(
        string='Cut-off Tax Amount', currency_field='company_currency_id',
        readonly=True, help="Tax Cut-off Amount in the company currency.")
    currency_id = fields.Many2one(
        related='parent_id.currency_id', string='Currency')
    company_currency_id = fields.Many2one(
        related='parent_id.company_currency_id',
        string="Company Currency")


class AccountCutoffMapping(models.Model):
    _name = 'account.cutoff.mapping'
    _description = 'Account Cut-off Mapping'
    _rec_name = 'account_id'

    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env['res.company']._company_default_get())
    account_id = fields.Many2one(
        'account.account', string='Regular Account',
        domain=[('deprecated', '=', False)], required=True)
    cutoff_account_id = fields.Many2one(
        'account.account', string='Cut-off Account',
        domain=[('deprecated', '=', False)], required=True)
    cutoff_type = fields.Selection([
        ('all', 'All Cut-off Types'),
        ('accrued_revenue', 'Accrued Revenue'),
        ('accrued_expense', 'Accrued Expense'),
        ('prepaid_revenue', 'Prepaid Revenue'),
        ('prepaid_expense', 'Prepaid Expense'),
        ], string='Cut-off Type', required=True)

    @api.model
    def _get_mapping_dict(self, company_id, cutoff_type='all'):
        """return a dict with:
        key = ID of account,
        value = ID of cutoff_account"""
        if cutoff_type == 'all':
            cutoff_type_filter = ('all', )
        else:
            cutoff_type_filter = ('all', cutoff_type)
        mappings = self.search([
            ('company_id', '=', company_id),
            ('cutoff_type', 'in', cutoff_type_filter),
            ])
        mapping = {}
        for item in mappings:
            mapping[item.account_id.id] = item.cutoff_account_id.id
        return mapping
