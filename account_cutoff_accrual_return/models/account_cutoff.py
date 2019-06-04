# -*- coding: utf-8 -*-
# Copyright 2018 Jacques-Etienne Baudoux (BCIM sprl) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, exceptions, fields, models


class AccountCutoff(models.Model):
    _inherit = 'account.cutoff'

    type = fields.Selection(selection_add=[
        ('accrued_revenue_return', 'Accrued Revenue Returns'),
        ('accrued_expense_return', 'Accrued Expense Returns'),
        ])

    @api.model
    def _default_cutoff_account_id(self):
        """ Set up default account for a new cutoff """
        account_id = super(AccountCutoff, self)._default_cutoff_account_id()
        type_cutoff = self.env.context.get('default_type')
        company = self.env.user.company_id
        if type_cutoff == 'accrued_expense_return':
            account_id = company.default_accrued_expense_return_account_id.id\
                or False
        elif type_cutoff == 'accrued_revenue_return':
            account_id = company.default_accrued_revenue_return_account_id.id\
                or False
        return account_id

    @api.model
    def _get_default_journal(self):
        journal = super(AccountCutoff, self)._get_default_journal()
        cutoff_type = self.env.context.get('default_type', False)
        if cutoff_type == 'accrued_expense_return':
            journal = self.env.user.company_id\
                .default_accrual_expense_journal_id.id or journal
        elif cutoff_type == 'accrued_revenue_return':
            journal = self.env.user.company_id\
                .default_accrual_revenue_journal_id.id or journal
        return journal

    @api.onchange('type')
    def _onchange_type(self):
        type = self.type
        label = super(AccountCutoff, self)._default_move_label()
        if type == 'accrued_expense_return':
            label = _('Accrued Expense Returns')
        elif type == 'accrued_revenue_return':
            label = _('Accrued Revenue Returns')
        self.move_label = label

    def _prepare_lines_return(self, line):
        assert self.type in ('accrued_expense_return',
                             'accrued_revenue_return'),\
            "The field 'type' has a wrong value"

        price_unit = line.price_unit_on_quant
        quantity = line.quantity
        amount = price_unit * quantity

        if self.type == 'accrued_expense_return':
            # Processing purchase order line
            account_id = line.product_id.property_account_expense_id.id
            if not account_id:
                account_id = line.product_id.product_tmpl_id.categ_id.\
                    property_account_expense_categ_id.id
            if not account_id:
                raise exceptions.UserError(
                    _("Error: Missing expense account on product '%s' or on "
                        "related product category.") % (line.product_id.name))
        elif self.type == 'accrued_revenue_return':
            # Processing sale order line
            account_id = line.product_id.property_account_income_id.id
            if not account_id:
                account_id = line.product_id.product_tmpl_id.categ_id.\
                    property_account_income_categ_id.id
            if not account_id:
                raise exceptions.UserError(
                    _("Error: Missing income account on product '%s' or on "
                      "related product category.") % (line.product_id.name))

        # currency_id = currency.id
        if self.type == 'accrued_expense':
            amount = amount * -1

        # we use account mapping here
        account_mapping = self.env['account.cutoff.mapping']._get_mapping_dict(
            self.company_id.id, self.type)
        accrual_account_id = account_mapping.get(account_id, account_id)

        res = {
            'parent_id': self.id,
            'name': line.product_id.display_name,
            'product_id': line.product_id.id,
            'account_id': account_id,
            'cutoff_account_id': accrual_account_id,
            'quantity': quantity,
            'price_unit': price_unit,
            'amount': amount,
            'cutoff_amount': amount,
        }
        return res

    def get_lines(self):
        """ Get inventory based on return location """
        lines = super(AccountCutoff, self).get_lines()
        domain = [('quantity', '>', 0)]
        if self.type == 'accrued_revenue_return':
            # customer returns
            domain += [('location_id.accrued_customer_return', '=', True)]
            lines = self.env['stock.history'].search(domain)
        elif self.type == 'accrued_expense_return':
            # supplier returns
            domain += [('location_id.accrued_supplier_return', '=', True)]
            lines = self.env['stock.history'].search(domain)
        else:
            return lines

        for line in lines:
            self.env['account.cutoff.line'].create(
                self._prepare_lines_return(line))

    @api.model
    def _cron_cutoff_expense_return(self):
        self._cron_cutoff('accrued_expense_return')

    @api.model
    def _cron_cutoff_revenue_return(self):
        self._cron_cutoff('accrued_revenue_return')
