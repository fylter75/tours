# See LICENSE file for full copyright and licensing details.
{
    "name": "Tours and Travel Management System - All in one (Except Portal)",
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "maintainer": "Serpent Consulting Services Pvt. Ltd.",
    "summary": """Tours and Travel management system""",
    "description": """This module allows to manage the management
                    of the tours and travels packages.""",
    "category": "Tours & Travels",
    "website": "http://www.serpentcs.com",
    "license": "AGPL-3",
    "version": "15.0.1.0.0",
    "sequence": 1,
    "depends": [
        "tour_travel_crm",
        "tour_travel_meal_management",
        "tour_travel_ticket_management",
        "tour_travel_extra_expenses",
        "tour_travel_transportation",
        "tour_travel_hotel_management",
    ],
    "data": [],
    "images": ["static/src/img/tour-pkg.jpg"],
    "installable": True,
    "price": 1,
    "currency": "EUR",
}
