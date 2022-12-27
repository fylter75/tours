# See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class SaleOrderTemplate(models.Model):
    _inherit = "sale.order.template"

    image_medium = fields.Binary("Medium-sized image")
    package_images = fields.One2many("package.image", "package_sale_id", "Images")
