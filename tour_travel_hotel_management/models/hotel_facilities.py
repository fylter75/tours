# See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class HotelFacilities(models.Model):
    _name = "hotel.facilities"
    _description = "Hotel Facilities"

    name = fields.Char(string="Facility Name")
    hotel_id = fields.Many2one("res.partner", "Hotel")
