#  See LICENSE file for full copyright and licensing details.
{
    "name": "Tours & Travels Ticket Management",
    "version": "15.0.1.0.0",
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "sequence": 1,
    "license": "AGPL-3",
    "category": "Tours & Travels",
    "website": "http://www.serpentcs.com",
    "description": """
        Tours & Travels Ticket Management
    """,
    "summary": """
        Tours & Travels Ticket Management
    """,
    "depends": ["tour_travel_management"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_view.xml",
        "views/ticket_view.xml",
        "views/tour_registration_view.xml",
        "report/report_quotation_ticket_package.xml",
    ],
    "demo": ["demo/ticketing_data.xml"],
    "installable": True,
    "application": True,
    "price": 65,
    "currency": "EUR",
}
