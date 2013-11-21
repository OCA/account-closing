## -*- coding: utf-8 -*-
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <style type="text/css">
            .overflow_ellipsis {
                text-overflow: ellipsis;
                overflow: hidden;
                white-space: nowrap;
            }
            ${css}
        </style>
    </head>
    <body>
<%setLang(user.lang)%>
        <div class="act_as_table data_table">
            <div class="act_as_row labels">
                <div class="act_as_cell">${_('Report')}</div>
                <div class="act_as_cell">${_('Fiscal Period')}</div>
                <div class="act_as_cell">${_('Company')}</div>
                <div class="act_as_cell">${_('Company currency')}</div>
            </div>
            <div class="act_as_row">
                <div class="act_as_cell">${_('Currency Gain and Loss')}</div>
                <div class="act_as_cell">${data.get('form', dict()).get('period_name')}</div>
                <div class="act_as_cell">${user.company_id.name}</div>
                <div class="act_as_cell">${user.company_id.currency_id.name}</div>
            </div>
        </div>
%for account in objects:
     <div class="act_as_table list_table" style="margin-top: 10px;">
                <div class="act_as_caption account_title">
                    ${account.code} - ${account.name}
                </div>
                <div class="act_as_thead">
                   <div class="act_as_row labels">
                      <div class="act_as_cell first_column">${_('Partner')}</div>
                      <div class="act_as_cell first_column amount" style="width: 100px;">${_('Curr. Balance YTD')}</div>
                      <div class="act_as_cell first_column amount" style="width: 50px;"></div>
                      <div class="act_as_cell first_column amount" style="width: 80px;">${_('Revaluation Rate')}</div>
                      <div class="act_as_cell first_column amount" style="width: 150px;">${_('Revaluated Amount YTD')}</div>
                      <div class="act_as_cell first_column amount" style="width: 100px;">${_('Balance YTD')}</div>
                      <div class="act_as_cell first_column amount" style="width: 100px;">${_('Gain(+)/Loss(-) YTD')}</div>
                      </div>
                   </div>
               %for line in account.ordered_lines:
               <div class="act_as_row lines">
                <div class="act_as_cell">${line.get('name', '--')}</div>
                <div class="act_as_cell amount" style="width: 100px;">${formatLang(line.get('gl_foreign_balance',0.0), monetary=True)}</div>
                <div class="act_as_cell" style="width: 50px;">${line.get('curr_name', '--')}</div>
                <div class="act_as_cell amount" style="width: 80px;">${'%.5f' % (line.get('gl_currency_rate', 0.0))}</div>
                <div class="act_as_cell amount" style="width: 150px;">${formatLang(line.get('gl_revaluated_balance', 0.0), monetary=True)}</div>
                <div class="act_as_cell amount" style="width: 100px;">${formatLang(line.get('gl_balance', 0.0), monetary=True)}</div>
                <div class="act_as_cell amount" style="width: 100px;">${formatLang(line.get('gl_ytd_balance', 0.0), monetary=True)}</div>
               </div>
               %endfor
               <div class="act_as_row lines labels">
                <div class="act_as_cell"><b>${_('TOTAL')}</b></div>
                <div class="act_as_cell"></div>
                <div class="act_as_cell"></div>
                <div class="act_as_cell"></div>
                <div class="act_as_cell amount"><b>${formatLang(account.gl_revaluated_balance_total or 0.0, monetary=True)}</b></div>
                <div class="act_as_cell amount"><b>${formatLang(account.gl_balance_total or 0.0, monetary=True)}</b></div>
                <div class="act_as_cell amount"><b>${formatLang(account.gl_ytd_balance_total or 0.0, monetary=True)}</b></div>
               </div>
     </div>
     <br/>
%endfor


    </body>
</html>
