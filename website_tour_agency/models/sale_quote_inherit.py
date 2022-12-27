# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Packagetags(models.Model):
    _name = "package.tag"

    name = fields.Char("Package Tag")


class Hoteltags(models.Model):
    _name = "hotel.tag"

    name = fields.Char("Hotel Tag")


class SaleOrderInheritForWebsite(models.Model):
    _inherit = "sale.order"

    image_medium = fields.Binary("Medium-sized image")
    package_tag = fields.Many2one(
        "package.tag", "Package Tag", help="This Tag will be display on package."
    )
    package_overview = fields.Text("Overview")
    package_images = fields.One2many("package.image", "package_variant_id", "Images")


class ProductImage(models.Model):
    _name = "product.template.image"
    name = fields.Char(string="Name")
    image = fields.Binary(string="Image")
    image_small = fields.Binary(string="Small Image")
    product_template_id = fields.Many2one(
        "product.template", "Product Images", copy=False
    )


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.depends("list_price")
    def _compute_currency_convert(self):
        """
        convert the currency to related company's currency.
         ---------------------------------
        @param self : object pointer
        """
        cur_obj = self.env["res.currency"]
        for rec in self:
            from_currency = rec.company_id.currency_id
            cur_id = cur_obj.browse(3)
            compute_currency = from_currency.compute(rec.list_price, cur_id)
            rec.converted_amount = compute_currency

    converted_amount = fields.Float(
        compute="_compute_currency_convert", string="Amount Converted", store=True
    )
    product_images = fields.One2many(
        "product.template.image", "product_template_id", "Images"
    )
    hotel_tag = fields.Many2one(
        "hotel.tag", "Hotel Tag", help="This Tag will be display on hotel."
    )
    rating = fields.Selection(
        [
            ("0", "None"),
            ("1", "Bad"),
            ("2", "Average"),
            ("3", "Good"),
            ("4", "Very Good"),
            ("5", "Excellent"),
        ],
        "Product rating",
        index=True,
    )
    street = fields.Char("Street")
    street2 = fields.Char("Street2")
    zip = fields.Char("Zip", change_default=True)
    city = fields.Char("City")
    state_id = fields.Many2one("res.country.state", string="State")
    country_id = fields.Many2one("res.country", string="Country")
    hotel_ok = fields.Boolean("Is Hotel ?", default=False)


class HotelInformationLine(models.Model):
    _inherit = "product.category"

    @api.depends("product_count")
    def _compute_get_product_name(self):
        """
        get the products which fall in defined category.
         ---------------------------------
        @param self : object pointer
        """
        for rec in self:
            products = self.env["product.template"].search(
                [("categ_id", "in", rec.ids)]
            )
            product_name_list = []
            for product in products:
                product_name_list.append(product.name)
            rec.product_list = ", ".join(product_name_list)

    product_list = fields.Char(compute="_compute_get_product_name")


class PackageImage(models.Model):
    _name = "package.image"

    name = fields.Char(string="Name")
    image = fields.Binary(string="Image")
    image_small = fields.Binary(string="Small Image")
    package_variant_id = fields.Many2one(
        "sale.quote.template", "Package Images", copy=False
    )
