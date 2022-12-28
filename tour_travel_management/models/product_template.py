#  See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"
    _description = "Tours and Travels products"

    type_travel_product = fields.Selection(
        [
            ("tickets", "Tickets"),
            ("extra_tickets", "Extra Tickets"),
            ("tour", "Tour"),
            ("visa", "Visa"),
            ("guide", "Guide"),
            ("other", "Other"),
        ],
        "Travel Product Type",
    )
