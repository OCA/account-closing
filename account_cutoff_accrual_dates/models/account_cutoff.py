# -*- coding: utf-8 -*-
# Copyright 2013-2018 Akretion France
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountCutoff(models.Model):
    _inherit = 'account.cutoff'

    @api.model
    def _get_default_source_journals(self):
        res = super(AccountCutoff, self)._get_default_source_journals()
        cutoff_type = self._context.get('default_type')
        mapping = {
            'accrued_expense': 'purchase',
            'accrued_revenue': 'sale',
            }
        if cutoff_type in mapping:
            src_journals = self.env['account.journal'].search(
                [('type', '=', mapping[cutoff_type])])
            if src_journals:
                res = src_journals.ids
        return res

    def _prepare_accrual_date_lines(self, aml, mapping):
        self.ensure_one()
        ato = self.env['account.tax']
        start_date_dt = fields.Date.from_string(aml.start_date)
        end_date_dt = fields.Date.from_string(aml.end_date)
        # Here, we compute the amount of the cutoff
        # That's the important part !
        total_days = (end_date_dt - start_date_dt).days + 1
        cutoff_date_str = self.cutoff_date
        cutoff_date_dt = fields.Date.from_string(cutoff_date_str)
        if end_date_dt <= cutoff_date_dt:
            prepaid_days = total_days
        else:
            prepaid_days = (cutoff_date_dt - start_date_dt).days + 1
        assert total_days > 0,\
            'Should never happen. Total days should always be > 0'
        cutoff_amount = (aml.credit - aml.debit) *\
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
            'tax_line_ids': [],
            }

        if aml.tax_ids:
            # It won't work with price-included taxes
            tax_res = aml.tax_ids.compute_all(
                cutoff_amount, product=aml.product_id, partner=aml.partner_id)
            for tax_line in tax_res['taxes']:
                tax = ato.browse(tax_line['id'])
                if tax.price_include:
                    raise UserError(_(
                        "Price included taxes such as '%s' are not "
                        "supported by the module account_cutoff_accrual_dates "
                        "for the moment.") % tax.display_name)
                if self.type == 'accrued_expense':
                    tax_account = tax.account_accrued_expense_id
                    if not tax_account:
                        raise UserError(_(
                            "Missing 'Accrued Expense Tax Account' "
                            "on tax '%s'") % tax.display_name)
                elif self.type == 'accrued_revenue':
                    tax_account = tax.account_accrued_revenue_id
                    if not tax_account:
                        raise UserError(_(
                            "Missing 'Accrued Revenue Tax Account' "
                            "on tax '%s'") % tax.display_name)
                res['tax_line_ids'].append((0, 0, {
                    'tax_id': tax_line['id'],
                    'base': cutoff_amount,
                    'amount': tax_line['amount'],
                    'sequence': tax_line['sequence'],
                    'cutoff_account_id': tax_account.id,
                    'cutoff_amount': tax_line['amount'],
                    }))
        return res

    def get_lines(self):
        res = super(AccountCutoff, self).get_lines()
        if self.type not in ['accrued_expense', 'accrued_revenue']:
            return res
        aml_obj = self.env['account.move.line']
        line_obj = self.env['account.cutoff.line']
        mapping_obj = self.env['account.cutoff.mapping']
        if not self.source_journal_ids:
            raise UserError(_(
                "You should set at least one Source Journal."))
        cutoff_date_str = self.cutoff_date

        domain = [
            ('start_date', '!=', False),
            ('journal_id', 'in', self.source_journal_ids.ids),
            ('start_date', '<=', cutoff_date_str),
            ('date', '>', cutoff_date_str)
            ]

        # Search for account move lines in the source journals
        amls = aml_obj.search(domain)
        # Create mapping dict
        mapping = mapping_obj._get_mapping_dict(self.company_id.id, self.type)

        # Loop on selected account move lines to create the cutoff lines
        for aml in amls:
            line_obj.create(self._prepare_accrual_date_lines(aml, mapping))
        return res
