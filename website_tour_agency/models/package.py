# See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class PackageCategory(models.Model):
    _name = "package.category"
    _inherit = ["package.category", "website.seo.metadata", "website.published.mixin"]

    image = fields.Binary()


class PackageImage(models.Model):
    _name = "package.image"
    _description = "Package Image"

    name = fields.Char(string="Name")
    image = fields.Binary(string="Image")
    image_small = fields.Binary(string="Small Image")
    package_sale_id = fields.Many2one("sale.order.template", copy=False)
