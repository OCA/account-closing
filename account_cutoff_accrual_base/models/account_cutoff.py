###############################################################################
# For copyright and license notices, see __manifest__.py file in root directory
###############################################################################


from odoo import api, fields, models
import odoo.addons.decimal_precision as dp


class AccountCutOff(models.Model):
    _inherit = 'account.cutoff'

    @api.model
    def _default_cutoff_account_id(self):
        account_id = super()._default_cutoff_account_id()
        cutoff_type = self.env.context.get('type')
        company = self.env.user.company_id
        if cutoff_type == 'accrued_expense':
            account_id = company.default_accrued_expense_account_id.id or False
        elif cutoff_type == 'accrued_revenue':
            account_id = company.default_accrued_revenue_account_id.id or False
        return account_id

    @api.model
    def _get_default_journal(self):
        journal_id = super()._get_default_journal()
        cutoff_type = self.env.context.get('type', False)
        default_journal_id = self.env.user.company_id\
            .default_cutoff_journal_id.id or False
        if cutoff_type == 'accrued_expense':
            journal_id = self.env.user.company_id\
                .default_accrual_expense_journal_id.id or default_journal_id
        elif cutoff_type == 'accrued_revenue':
            journal_id = self.env.user.company_id\
                .default_accrual_revenue_journal_id.id or default_journal_id
        return journal_id


class AccountCutoffLine(models.Model):
    _inherit = 'account.cutoff.line'

    quantity = fields.Float(
        digits=dp.get_precision('Product UoS'),
        readonly=True)
    price_unit = fields.Float(
        string='Unit Price',
        digits=dp.get_precision('Product Price'),
        readonly=True,
        help="Price per unit (discount included)")
