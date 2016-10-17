# -*- coding: utf-8 -*-
# © 2013-2016 Akretion (Alexis de Lattre <alexis.delattre@akretion.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, fields, api, _
from openerp.exceptions import UserError, ValidationError


class AccountCutoff(models.Model):
    _inherit = 'account.cutoff'

    @api.model
    def _get_default_source_journals(self):
        res = []
        type = self._context.get('type')
        mapping = {
            'prepaid_expense': 'purchase',
            'prepaid_revenue': 'sale',
            }
        if type in mapping:
            src_journals = self.env['account.journal'].search(
                [('type', '=', mapping[type])])
            if src_journals:
                res = src_journals.ids
        return res

    source_journal_ids = fields.Many2many(
        'account.journal', id1='cutoff_id', id2='journal_id',
        string='Source Journals', readonly=True,
        default=_get_default_source_journals,
        states={'draft': [('readonly', False)]})
    forecast = fields.Boolean(
        string='Forecast',
        readonly=True, states={'draft': [('readonly', False)]},
        help="The Forecast mode allows the user to compute "
        "the prepaid revenue/expense between 2 dates in the future.")
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')

    _sql_constraints = [(
        'date_type_forecast_company_uniq',
        'unique('
        'cutoff_date, company_id, type, forecast, start_date, end_date)',
        'A cut-off of the same type already exists with the same date(s) !'
        )]

    @api.multi
    @api.constrains('start_date', 'end_date', 'forecast')
    def _check_start_end_dates(self):
        for prepaid in self:
            if prepaid.forecast and prepaid.start_date and prepaid.end_date \
                    and prepaid.start_date > prepaid.end_date:
                raise ValidationError(_(
                    'The start date is after the end date!'))

    @api.onchange('forecast')
    def forecast_onchange(self):
        return {'warning': {
            'title': _('Warning'),
            'message': _(
                "Don't forget to Re-Generate Lines after entering or "
                "leaving forecast mode.")}}

    @api.multi
    def _prepare_prepaid_lines(self, aml, mapping):
        self.ensure_one()
        start_date_dt = fields.Date.from_string(aml.start_date)
        end_date_dt = fields.Date.from_string(aml.end_date)
        # Here, we compute the amount of the cutoff
        # That's the important part !
        total_days = (end_date_dt - start_date_dt).days + 1
        if self.forecast:
            out_days = 0
            forecast_start_date_dt = fields.Date.from_string(self.start_date)
            forecast_end_date_dt = fields.Date.from_string(self.end_date)
            if end_date_dt > forecast_end_date_dt:
                out_days += (end_date_dt - forecast_end_date_dt).days
            if start_date_dt < forecast_start_date_dt:
                out_days += (forecast_start_date_dt - start_date_dt).days
            prepaid_days = total_days - out_days
        else:
            cutoff_date_str = self.cutoff_date
            cutoff_date_dt = fields.Date.from_string(cutoff_date_str)
            if start_date_dt > cutoff_date_dt:
                prepaid_days = total_days
            else:
                prepaid_days = (end_date_dt - cutoff_date_dt).days
        assert total_days > 0,\
            'Should never happen. Total days should always be > 0'
        cutoff_amount = (aml.debit - aml.credit) *\
            prepaid_days / float(total_days)
        # we use account mapping here
        if aml.account_id.id in mapping:
            cutoff_account_id = mapping[aml.account_id.id]
        else:
            cutoff_account_id = aml.account_id.id

        res = {
            'parent_id': self.id,
            'move_line_id': aml.id,
            'partner_id': aml.partner_id.id or False,
            'name': aml.name,
            'start_date': start_date_dt,
            'end_date': end_date_dt,
            'account_id': aml.account_id.id,
            'cutoff_account_id': cutoff_account_id,
            'analytic_account_id': aml.analytic_account_id.id or False,
            'total_days': total_days,
            'prepaid_days': prepaid_days,
            'amount': aml.credit - aml.debit,
            'currency_id': self.company_currency_id.id,
            'cutoff_amount': cutoff_amount,
            }
        return res

    @api.multi
    def get_prepaid_lines(self):
        self.ensure_one()
        aml_obj = self.env['account.move.line']
        line_obj = self.env['account.cutoff.line']
        mapping_obj = self.env['account.cutoff.mapping']
        if not self.source_journal_ids:
            raise UserError(
                _("You should set at least one Source Journal."))
        cutoff_date_str = self.cutoff_date
        # Delete existing lines
        self.line_ids.unlink()

        if self.forecast:
            domain = [
                ('start_date', '<=', self.end_date),
                ('end_date', '>=', self.start_date),
                ('journal_id', 'in', self.source_journal_ids.ids)
                ]
        else:
            domain = [
                ('start_date', '!=', False),
                ('journal_id', 'in', self.source_journal_ids.ids),
                ('end_date', '>', cutoff_date_str),
                ('date', '<=', cutoff_date_str)
                ]

        # Search for account move lines in the source journals
        amls = aml_obj.search(domain)
        # Create mapping dict
        mapping = mapping_obj._get_mapping_dict(self.company_id.id, self.type)

        # Loop on selected account move lines to create the cutoff lines
        for aml in amls:
            line_obj.create(self._prepare_prepaid_lines(aml, mapping))
        return True

    @api.model
    def _inherit_default_cutoff_account_id(self):
        account_id = super(AccountCutoff, self).\
            _inherit_default_cutoff_account_id()
        type = self._context.get('type')
        company = self.env.user.company_id
        if type == 'prepaid_revenue':
            account_id = company.default_prepaid_revenue_account_id.id or False
        elif type == 'prepaid_expense':
            account_id = company.default_prepaid_expense_account_id.id or False
        return account_id


class AccountCutoffLine(models.Model):
    _inherit = 'account.cutoff.line'

    move_line_id = fields.Many2one(
        'account.move.line', string='Account Move Line', readonly=True)
    move_date = fields.Date(
        related='move_line_id.date', string='Account Move Date', readonly=True)
    invoice_id = fields.Many2one(
        related='move_line_id.invoice_id', string='Invoice', readonly=True)
    start_date = fields.Date(string='Start Date', readonly=True)
    end_date = fields.Date(string='End Date', readonly=True)
    total_days = fields.Integer('Total Number of Days', readonly=True)
    prepaid_days = fields.Integer(
        string='Prepaid Days', readonly=True,
        help="In regular mode, this is the number of days after the "
        "cut-off date. In forecast mode, this is the number of days "
        "between the start date and the end date.")
