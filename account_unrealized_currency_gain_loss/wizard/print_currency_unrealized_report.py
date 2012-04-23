from openerp.osv.orm import TransientModel, fields

class UnrealizedCurrencyReportPrinter(TransientModel):
    _name = "unrealized.report.printer"

    _columns = {'chart_account_id': fields.many2one('account.account', 'Chart root',
                                domain=[('parent_id', '=', False)]),
               'period_id': fields.many2one('account.period', 'Period to use',required=True)}


    def print_report(self, cursor, uid, wid, data, context=None):
        context = context or {}
        # we update form with display account value
        if isinstance(wid, list):
            wid = wid[0]
        current = self.browse(cursor, uid, wid, context)
        form = {}
        form['period_id'] = current.period_id.id
        form['period_name'] = current.period_id.name
        form['account_ids'] = [current.chart_account_id.id]
        data['form'] = form
        print data
        return {'type': 'ir.actions.report.xml',
                'report_name': 'currency_unrealized',
                'datas': data}
