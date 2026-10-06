import {registry} from "@web/core/registry";

const createClosingFromTemplate = () => [
    {
        content: "Create a fiscal year closing",
        trigger: ".o_list_button_add",
        run: "click",
    },
    {
        content: "Type the closing template",
        trigger: ".o_field_widget[name=closing_template_id] input",
        run: "edit Closing template",
    },
    {
        content: "Pick the closing template",
        trigger:
            ".o-autocomplete--dropdown-item:contains(Closing template):not(:contains(Create))",
        run: "click",
    },
    {
        content: "Close the current year, where the test moves are",
        trigger: ".o_field_widget[name=year] input",
        run: `edit ${new Date().getFullYear()}`,
    },
    {
        content: "The template fills the move configurations",
        trigger: ".o_field_widget[name=move_config_ids] .o_data_row:nth-child(3)",
    },
];

registry.category("web_tour.tours").add("account_fiscal_year_closing_flow", {
    steps: () => [
        ...createClosingFromTemplate(),
        {
            content: "Calculate the closing moves",
            trigger: "button[name=button_calculate]",
            run: "click",
        },
        {
            content: "The closing is processed",
            trigger: ".o_statusbar_status .o_arrow_button_current:contains(Processed)",
        },
        {
            content: "Confirm and post the moves",
            trigger: "button[name=button_post]",
            run: "click",
        },
        {
            content: "The closing is posted",
            trigger: ".o_statusbar_status .o_arrow_button_current:contains(Posted)",
        },
        {
            content: "Open the closing moves",
            trigger: "button[name=button_open_moves]",
            run: "click",
        },
        {
            content: "The closing moves are listed",
            trigger: ".o_breadcrumb:contains(Fiscal closing moves)",
        },
        {
            content: "The three closing moves are listed",
            trigger: ".o_list_view .o_data_row:nth-child(3) td:contains(MISC)",
        },
        {
            content: "Open a closing move",
            trigger: ".o_list_view .o_data_row:first-child td:contains(MISC)",
            run: "click",
        },
        {
            content: "The move shows its closing type",
            trigger: ".o_form_view .o_field_widget[name=closing_type]",
        },
    ],
});

registry.category("web_tour.tours").add("account_fiscal_year_closing_unbalanced", {
    steps: () => [
        ...createClosingFromTemplate(),
        {
            content: "Calculate the closing moves",
            trigger: "button[name=button_calculate]",
            run: "click",
        },
        {
            content: "The wizard lists the unbalanced move",
            trigger: ".modal .o_form_view .o_field_widget[name=line_ids] .o_data_row",
        },
    ],
});

registry.category("web_tour.tours").add("account_fiscal_year_closing_template", {
    steps: () => [
        {
            content: "Open the closing template",
            trigger: ".o_list_view .o_data_row td[name=name]",
            run: "click",
        },
        {
            content: "The template shows its move configurations",
            trigger: ".o_form_view .o_field_widget[name=move_config_ids] .o_data_row",
        },
    ],
});
