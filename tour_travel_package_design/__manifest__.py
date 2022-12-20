#  -*- coding: utf-8 -*-
#  See LICENSE file for full copyright and licensing details.
{
    'name': 'Tours & Travels Package Design Management',
    'version': '12.0.1.0.0',
    'author': 'Serpent Consulting Services Pvt. Ltd.',
    'sequence': 1,
    'license': 'LGPL-3',
    'category': 'Sales',
    'website': 'http://www.serpentcs.com',
    'depends': ['sale_management', 'purchase', 'stock',
                'hr_contract', 'web','website_sale_stock',
                'web_widget_date_validation'],
    'description': """
    Tour Travel Package Design
    Hospitality
    Travel agency
    Tour agency
    Tours and travel
    tour package design
    visa tourist hotel booking
    ticket booking
    hotel booking
    package booking
    visa management
    tourist guide management
    transport management
    tourism industry
    travel planning
    route plan
    group tour packages
    online package design
    online hotel booking
    online tour travel management
    Tour Travel Agency Management
    Tours & Travels Agency Management
    """,
    'summary': """
    Tour Travel Package Design
    Tours & Travels Agency Management
    """,
    'data': ['security/ir.model.access.csv',
             'security/security_group.xml',
             'views/menu_configuration_view.xml',
             'views/sale_order_view.xml',
             'views/res_partner_view.xml',
             'views/product_view.xml',
             'views/travel_package_view.xml',
             'views/contract_view.xml',
             'views/report_view.xml',
             'views/package_report_view.xml',
             'views/invoice_package_report_view.xml',
             'report/purchase_rfq_qweb_view.xml',
             'views/qweb_po_package_report_view.xml',
             'views/booking_ref_with_room_list_report_view.xml',
             'views/rfq_quote_report_view.xml',
             'views/customer_group_cost_report_view.xml',
             'views/customer_quote_report_view.xml',
             'views/inherit_so_report_view.xml',
             'views/purchase_order_view.xml',
             'data/menu_type_data_view.xml',
             'data/visa_satus_view.xml',
             'data/airline_data_view.xml',
             'data/visa_docs_data_view.xml',
             'data/airport_data_view.xml',
             'data/hotel_facilities_view.xml',
             'data/room_data.xml',
             'data/product_category_data.xml',
             'data/product_data.xml',
             'data/contract_type_data.xml',
             'data/contract_data.xml',
             'data/contract_information_data.xml',
             'data/product_image_demo.xml',
             ],
    'images': ['static/src/img/tour-pkg.jpg'],
    'installable': True,
    'application': False,
    'auto_install': False,
    'price': 219,
    'currency': 'EUR',
}
