# Copyright 2012-2018 Camptocamp SA
# Copyright 2022 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import api, models


class ShellAccount(object):

    """Small class that avoid to override account account object.

    only for pure performance reason.
    Browsing an account account object is not efficient
    because of function fields
    This object aims to be easily transposed to account account if needed
    """

    def __init__(self, account):
        self.cursor = account.env.cr
        tmp = account.read(["id", "name", "code", "currency_revaluation"])
        self.account_id = tmp[0]["id"]
        self.ordered_lines = []
        self.keys_to_sum = [
            "gl_foreign_balance",
            "gl_currency_rate",
            "gl_revaluated_balance",
            "gl_balance",
            "gl_ytd_balance",
        ]

    def __contains__(self, key):
        return hasattr(self, key)

    def get_lines(self, start_date, end_date, only_include_posted_entries):
        """Get all line account move line that are need on report for current
        account.
        """
        sql = (
            """
              SELECT rp.name,
              aml.date,
              aml.gl_foreign_balance,
              aml.gl_currency_rate,
              aml.gl_revaluated_balance,
              aml.gl_balance,
              aml.gl_revaluated_balance -
              aml.gl_balance as gl_ytd_balance,
              rc.name as curr_name
              FROM account_move_line aml
              LEFT JOIN res_partner rp ON
                (aml.partner_id = rp.id)
              LEFT JOIN account_move am ON
                (aml.move_id = am.id)
              LEFT JOIN res_currency rc ON
                (aml.currency_id = rc.id)
              WHERE aml.account_id = %s
                AND aml.gl_balance IS NOT NULL
                AND aml.gl_balance != 0
                AND am.state IN %s
                """
            + (("AND aml.date >= %s") if start_date else "")
            + """
                """
            + (("AND aml.date <= %s") if end_date else "")
            + """
              ORDER BY rp.name,
                aml.gl_foreign_balance,
                aml.date ASC
              """
        )
        params = [self.account_id]
        states = ["posted"]
        states += not only_include_posted_entries and ["draft"] or []
        params.append(tuple(states))
        if start_date:
            params.append(start_date)
        if end_date:
            params.append(end_date)
        self.cursor.execute(sql, params=params)
        self.ordered_lines = self.cursor.dictfetchall()
        return self.ordered_lines

    def compute_totals(self):
        """Compute the sum of values in self.ordered_lines"""
        totals = dict.fromkeys(self.keys_to_sum, 0.0)
        for line in self.ordered_lines:
            for tot in self.keys_to_sum:
                totals[tot] += line.get(tot, 0.0)
        for key, val in totals.items():
            setattr(self, key + "_total", val)


class CurrencyUnrealizedReport(models.AbstractModel):
    _name = "report.account_multicurrency_revaluation.curr_unrealized_report"
    _description = "Currency Unrealized Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        shell_accounts = {}
        start_date = data.get("start_date", False)
        end_date = data.get("end_date", False)
        only_include_posted_entries = data.get("only_include_posted_entries", False)
        account_ids = data.get("account_ids", False)
        docs = self.env["account.account"]
        accounts = docs.browse(account_ids)
        for account in accounts:
            acc = ShellAccount(account)
            acc.get_lines(start_date, end_date, only_include_posted_entries)
            if acc.ordered_lines:
                docs |= account
                shell_accounts[account.id] = acc
                acc.compute_totals()
        docargs = {
            "doc_ids": docs.ids,
            "doc_model": "account.account",
            "docs": docs,
            "shell_accounts": shell_accounts,
            "data": data.get("form", False),
        }
        return docargs
