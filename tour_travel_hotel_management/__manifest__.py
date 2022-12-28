#  See LICENSE file for full copyright and licensing details.
{
    "name": "Tours & Travels Hotel Management",
    "version": "15.0.1.0.0",
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "sequence": 1,
    "license": "AGPL-3",
    "category": "Tours & Travels",
    "website": "http://www.serpentcs.com",
    "description": """
        Tours & Travels Hotel Management
    """,
    "summary": """
        Tours & Travels Hotel Management
    """,
    "depends": ["tour_travel_management"],
    "data": [
        "security/ir.model.access.csv",
        "views/hotel_view.xml",
        "views/hotel_facilities_view.xml",
        "views/hotel_room_view.xml",
        "views/tour_package_view.xml",
        "views/package_contract_view.xml",
        "views/tour_registration_view.xml",
        "report/report_hotel_quotation_package.xml",
        "report/report_hotel_agreement.xml",
    ],
    "demo": ["demo/hotel_data.xml"],
    "installable": True,
    "application": True,
    "price": 65,
    "currency": "EUR",
}
