# See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    rating = fields.Selection(selection_add=[("4", "Very Good"), ("5", "Excellent")])
    website_visible = fields.Boolean("Visible On Website", default=True)
    description = fields.Html("Overview")
