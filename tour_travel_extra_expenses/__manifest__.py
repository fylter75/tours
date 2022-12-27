#  See LICENSE file for full copyright and licensing details.
{
    "name": "Tours & Travels Extra Expenses",
    "version": "15.0.1.0.0",
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "sequence": 1,
    "license": "AGPL-3",
    "category": "Tours & Travels",
    "website": "http://www.serpentcs.com",
    "description": """
        Tours & Travels Extra Expenses
    """,
    "summary": """
        Tours & Travels Extra Expenses
    """,
    "depends": ["tour_travel_management"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_template_view.xml",
        "views/guide_registration_view.xml",
        "views/extra_ticket_view.xml",
        "report/report_quotation_guide_package.xml",
    ],
    "demo": ["demo/guide_data.xml"],
    "installable": True,
    "price": 65,
    "currency": "EUR",
}
