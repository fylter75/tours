# See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class Testimonial(models.Model):
    _name = "testimonial.testimonial"
    _description = "Testimonial"
    _inherit = ["mail.thread", "website.seo.metadata", "website.published.mixin"]

    name = fields.Char("Customer Name")
    image = fields.Binary("Customer Image")
    tour_name = fields.Char(
        "Feedback for",
        help="""Feedback for tour,visa,
                             transportation service""",
    )
    description = fields.Text("Description")
    sequence = fields.Integer(default="1")
