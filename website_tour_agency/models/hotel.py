# See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class HotelFacility(models.Model):

    _inherit = "hotel.facilities"

    icon_class = fields.Char(
        "Facility Icon",
        default="fa fa-check-circle-o",
        help="Add Font-awesome icon class",
    )
