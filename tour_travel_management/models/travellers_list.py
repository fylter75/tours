#  See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class TravellersList(models.Model):
    _name = "travellers.list"
    _description = "Travellers List"

    #    partner_id = fields.Many2one('res.partner','Name', required=True)
    name = fields.Char("Name", required=True)
    age = fields.Integer("Age", required=True, default=18)
    gender = fields.Selection(
        [("male", "Male"), ("female", "Female"), ("other", "Other")], string="Gender"
    )
    remarks = fields.Char("Remarks")
    identity_type = fields.Selection(
        [
            ("voter_id", "Voter ID"),
            ("driving license", "Driving License"),
            ("passport", "Passport Number"),
        ],
        string="ID Type",
    )
    identity_number = fields.Char("Identity Proof number")
    identities_images = fields.Many2many(
        "ir.attachment", string="Identity Proof", help="Multi Image upload"
    )
    color = fields.Integer(string="Color Index", default=0)
    package_id = fields.Many2one(
        "sale.order.template", "Package", domain=[("is_package", "=", True)]
    )
    sale_order_id = fields.Many2one("sale.order", "Order")
    invoice_id = fields.Many2one("account.move", "Invoice")
