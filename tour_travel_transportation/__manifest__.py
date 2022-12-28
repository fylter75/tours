#  See LICENSE file for full copyright and licensing details.
{
    "name": "Tours & Travels Transportation Management",
    "version": "15.0.1.0.0",
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "sequence": 1,
    "category": "Tours & Travels",
    "license": "AGPL-3",
    "website": "http://www.serpentcs.com",
    "description": """
        Tours & Travels Transportation Management
    """,
    "summary": """
        Tours & Travels Transportation Management
    """,
    "depends": ["tour_travel_management"],
    "data": [
        "security/ir.model.access.csv",
        "views/transportation_view.xml",
        "views/transportation_vehicle_view.xml",
        "views/package_contract_view.xml",
        "views/sale_order_view.xml",
        "views/tour_registration_view.xml",
        "report/report_quotation_transport_package.xml",
        "report/report_transport_agreement.xml",
    ],
    "demo": ["demo/transportation_data.xml"],
    "installable": True,
    "price": 65,
    "currency": "EUR",
}
