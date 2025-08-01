#  Copyright 2025 Giuseppe Borruso
#  License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    companies = env["res.company"].search([])
    chart_templates = {
        company.id: env["account.chart.template"]._guess_chart_template(
            company.country_id
        )
        for company in companies
    }
    for template in env["account.fiscalyear.closing.template"].search([]):
        if template.company_id:
            template.chart_template = chart_templates.get(template.company_id.id)
        else:
            first_company = companies[0]
            template.company_id = first_company
            template.chart_template = chart_templates.get(first_company.id)

            for company in companies[1:]:
                template.copy(
                    {
                        "company_id": company.id,
                        "chart_template": chart_templates.get(company.id),
                    }
                )

    for config in env["account.fiscalyear.closing.config.template"].search([]):
        company = config.journal_id.company_id
        template = env["account.fiscalyear.closing.template"].search(
            [
                ("chart_template", "=", chart_templates.get(company.id)),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        config.write({"template_id": template.id})

    for closing in env["account.fiscalyear.closing"].search([]):
        company = closing.company_id
        template = env["account.fiscalyear.closing.template"].search(
            [
                ("chart_template", "=", chart_templates.get(company.id)),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        closing.write({"closing_template_id": template.id})
