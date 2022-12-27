#  See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import get_lang


class TourRegistration(models.Model):
    _inherit = "sale.order"
    _description = "Tour Registration"

    tour_begin_date = fields.Date("Tour Start Date")
    tour_end_date = fields.Date("Tour End Date")
    tour_category_id = fields.Many2one("package.category", "Tour Category")
    passenger_ids = fields.One2many("travellers.list", "sale_order_id",
                                    "Passenger")
    is_registration = fields.Boolean("Is Registration")
    adults = fields.Integer("Adults", help="Above 12 years", default="1")
    children = fields.Integer("Children", help="Age Between 2-12 years")
    infants = fields.Integer("Infants", help="Below 2 years")
    group_costing_id = fields.Many2one(
        "group.costing.line", "Passenger Group", ondelete="restrict"
    )
    extra_service_ids = fields.One2many(
        "tour.registration.line", "extra_service_id", "Extra Services"
    )

    def get_group_cost(self):
        for rec in self:
            if (rec.adults + rec.children) >= 1:
                rec.onchange_sale_order_template_id()
            if rec.amount_untaxed != 0 and rec.group_costing_id:
                discount_amount = rec.group_costing_id.sales_price - rec.amount_untaxed
                if discount_amount:
                    product = (
                        self.env["ir.config_parameter"]
                        .sudo()
                        .get_param("tour_travel_management.product_discount_id")
                    )
                    if not product:
                        product = self.env.ref(
                            "tour_travel_management.package_discount"
                        )
                    lina_data = {
                        "order_id": rec.id,
                        "product_id": int(product),
                        "product_uom_qty": 1,
                        "product_uom": self.env["product.product"]
                        .browse(int(product))
                        .uom_id.id,
                        "name": "Package Discount",
                        "tax_id": False,
                        "price_unit": discount_amount,
                    }
                    self.extra_service_ids = [(0, 0, lina_data)]

    @api.onchange("group_costing_id")
    def _onchange_group_costing(self):
        self.adults = self.children = 0
        if self.group_costing_id:
            self.adults = self.group_costing_id.number_of_adult
            self.children = self.group_costing_id.number_of_children

    @api.constrains("tour_begin_date", "tour_end_date")
    def _check_begin_end_date(self):
        for package in self:
            if package.tour_begin_date and package.tour_end_date:
                if package.tour_begin_date < fields.Date.context_today(self):
                    raise ValidationError(
                _("""Arrival date should be greater than the Current Date.""")
                    )
                if package.tour_begin_date > package.tour_end_date:
                    raise ValidationError(
                    _("""Departure date should be greater than Arrival Date.""")
                    )

    def _create_invoices(self, grouped=False, final=False):
        invoice = super(TourRegistration, self)._create_invoices(
            grouped=False, final=False
        )
        if invoice and self.is_registration:
            invoice.package_id = self.sale_order_template_id.id
            for passenger in self.passenger_ids:
                if not passenger.invoice_id:
                    passenger.invoice_id = invoice.id
        return invoice

    def action_confirm(self):
        total_passengers = self.children + self.adults + self.infants
        res = super(TourRegistration, self).action_confirm()

        if not self.passenger_ids and self.env.context.get("tour_confirm"):
            raise UserError(_("Add Traveller Details."))
        elif not total_passengers == len(self.passenger_ids) and self.env.context.get(
            "tour_confirm"
        ):
            raise UserError(_("Total passengers not match."))
        return res

    def get_order_line_list(self):
        order_line_list = []
        return order_line_list

    @api.onchange("sale_order_template_id")
    def onchange_sale_order_template_id(self):
        for order in self:
            order.update(
                {
                    "currency_id": order.sale_order_template_id.selling_currency_id.id
                    or self.env.company.currency_id.id,
                    "tour_begin_date": order.sale_order_template_id.arrival_date,
                    "tour_end_date": order.sale_order_template_id.return_date,
                }
            )

    def action_save_passenger_details(self):
        return {
            "effect": {
                "fadeout": "slow",
                "message": "Record Saved Successfully!",
                "img_url": "/web/static/src/img/smile.svg",
                "type": "rainbow_man",
            }
        }


class TourRegistrationLine(models.Model):
    _name = "tour.registration.line"
    _description = "Tour Registration Line"

    @api.depends("product_uom_qty", "discount", "price_unit", "tax_id")
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(
                price,
                line.order_id.currency_id,
                line.product_uom_qty,
                product=line.product_id,
                partner=line.order_id.partner_shipping_id,
            )
            line.update(
                {
                    "price_tax": sum(
                        t.get("amount", 0.0) for t in taxes.get("taxes", [])
                    ),
                    "price_total": taxes["total_included"],
                    "price_subtotal": taxes["total_excluded"],
                }
            )

    extra_service_id = fields.Many2one(
        "sale.order", "Extra Service", ondelete="cascade"
    )
    order_line_id = fields.Many2one(
        "sale.order.line",
        "Sale Order Line",
        required=True,
        delegate=True,
        ondelete="cascade",
    )
    contract_id = fields.Many2one("package.contract", "Contract",
                    ondelete="restrict")
    price_subtotal = fields.Monetary(
        compute="_compute_amount", string="Subtotal", readonly=True, store=True
    )
    price_tax = fields.Float(
        compute="_compute_amount", string="Total Tax", readonly=True, store=True
    )
    price_total = fields.Monetary(
        compute="_compute_amount", string="Total", readonly=True, store=True
    )

    @api.model
    def create(self, vals):
        if "extra_service_id" in vals:
            sale = self.env["sale.order"].browse(vals["extra_service_id"])
            vals.update({"order_id": sale.id})
        return super(TourRegistrationLine, self).create(vals)

    def unlink(self):
        if self.order_line_id:
            self.order_line_id.unlink()
        return super(TourRegistrationLine, self).unlink()

    def _compute_tax_id(self):
        for line in self:
            fpos = (
                line.order_id.fiscal_position_id
                or line.order_id.partner_id.property_account_position_id
            )
            # If company_id is set, always filter taxes by the company
            taxes = line.product_id.taxes_id.filtered(
                lambda r: not line.company_id or r.company_id == line.company_id
            )
            line.tax_id = (
                fpos.map_tax(taxes, line.product_id, line.order_id.partner_shipping_id)
                if fpos
                else taxes
            )

    def _get_contract_price(self):
        return 0

    def _get_contract_cost_price(self):
        return 0

    def _get_product_descripation(self):
        return False

    def _compute_margin(self, order_id, product_id, product_uom_id):
        frm_cur = self.env.company.currency_id
        to_cur = order_id.pricelist_id.currency_id
        purchase_price = self._get_contract_cost_price()
        if purchase_price <= 0:
            purchase_price = product_id.standard_price
        if product_uom_id != product_id.uom_id:
            purchase_price = product_id.uom_id._compute_price(
                purchase_price, product_uom_id
            )
        price = frm_cur._convert(
            purchase_price,
            to_cur,
            order_id.company_id or self.env.company,
            order_id.date_order or fields.Date.today(),
            round=False,
        )
        return price

    def _get_real_price_currency(self, product, rule_id, qty, uom, pricelist_id):
        """Retrieve the price before applying the pricelist
            :param obj product: object of current product record
            :parem float qty: total quentity of product
            :param tuple price_and_rule: tuple(price,
                    suitable_rule) coming from pricelist computation
            :param obj uom: unit of measure of current order line
            :param integer pricelist_id: pricelist id of sales order"""
        PricelistItem = self.env["product.pricelist.item"]
        field_name = "lst_price"
        currency_id = None
        product_currency = product.currency_id
        if rule_id:
            pricelist_item = PricelistItem.browse(rule_id)
            if pricelist_item.pricelist_id.discount_policy == "without_discount":
                while (
                    pricelist_item.base == "pricelist"
                    and pricelist_item.base_pricelist_id
                    and pricelist_item.base_pricelist_id.discount_policy
                    == "without_discount"
                ):
                    price, rule_id = pricelist_item.base_pricelist_id.with_context(
                        uom=uom.id
                    ).get_product_price_rule(product, qty, self.order_id.partner_id)
                    pricelist_item = PricelistItem.browse(rule_id)

            if pricelist_item.base == "standard_price":
                field_name = "standard_price"
                product_currency = product.cost_currency_id
            elif (
                pricelist_item.base == "pricelist" and pricelist_item.base_pricelist_id
            ):
                field_name = "price"
                product = product.with_context(
                    pricelist=pricelist_item.base_pricelist_id.id
                )
                product_currency = pricelist_item.base_pricelist_id.currency_id
            currency_id = pricelist_item.pricelist_id.currency_id

        if not currency_id:
            currency_id = product_currency
            cur_factor = 1.0
        else:
            if currency_id.id == product_currency.id:
                cur_factor = 1.0
            else:
                cur_factor = currency_id._get_conversion_rate(
                    product_currency,
                    currency_id,
                    self.company_id or self.env.company,
                    self.order_id.date_order or fields.Date.today(),
                )

        product_uom = self.env.context.get("uom") or product.uom_id.id
        if uom and uom.id != product_uom:
            # the unit price is in a different uom
            uom_factor = uom._compute_price(1.0, product.uom_id)
        else:
            uom_factor = 1.0

        product_price = self._get_contract_price()
        if product_price <= 0:
            product_price = product[field_name]
        return product_price * uom_factor * cur_factor, currency_id

    def _get_display_price(self, product):
        # TO DO: move me in master/saas-16 on sale.order
        # awa: don't know if it's still the case since we
        # need the "product_no_variant_attribute_value_ids" field now
        # to be able to compute the full price

        # it is possible that a no_variant attribute is still in a variant if
        # the type of the attribute has been changed after creation.
        no_variant_attributes_price_extra = [
            ptav.price_extra
            for ptav in self.product_no_variant_attribute_value_ids.filtered(
                lambda ptav: ptav.price_extra
                and ptav not in product.product_template_attribute_value_ids
            )
        ]
        if no_variant_attributes_price_extra:
            product = product.with_context(
                no_variant_attributes_price_extra=tuple(
                    no_variant_attributes_price_extra
                )
            )

        if self.order_id.pricelist_id.discount_policy == "with_discount":
            product_price = self._get_contract_price()
            if product_price <= 0:
                product_price = product.with_context(
                    pricelist=self.order_id.pricelist_id.id
                ).price
            return product_price
        product_context = dict(
            self.env.context,
            partner_id=self.order_id.partner_id.id,
            date=self.order_id.date_order,
            uom=self.product_uom.id,
        )

        final_price, rule_id = self.order_id.pricelist_id.with_context(
            product_context
        ).get_product_price_rule(
            self.product_id, self.product_uom_qty or 1.0, self.order_id.partner_id
        )
        base_price, currency = self.with_context(
            product_context
        )._get_real_price_currency(
            product,
            rule_id,
            self.product_uom_qty,
            self.product_uom,
            self.order_id.pricelist_id.id,
        )
        if currency != self.order_id.pricelist_id.currency_id:
            base_price = currency._convert(
                base_price,
                self.order_id.pricelist_id.currency_id,
                self.order_id.company_id or self.env.company,
                self.order_id.date_order or fields.Date.today(),
            )
        # negative discounts (= surcharge) are included in the display price
        return max(base_price, final_price)

    @api.onchange("product_id")
    def product_id_change(self):
        if not self.product_id:
            return
        product_template = self.product_id.product_tmpl_id
        template_attribute = product_template.valid_product_template_attribute_line_ids
        valid_values = template_attribute.product_template_value_ids
        # remove the is_custom values that don't belong to this template
        for pacv in self.product_custom_attribute_value_ids:
            if pacv.custom_product_template_attribute_value_id not in valid_values:
                self.product_custom_attribute_value_ids -= pacv

        # remove the no_variant attributes that don't belong to this template
        for ptav in self.product_no_variant_attribute_value_ids:
            if ptav._origin not in valid_values:
                self.product_no_variant_attribute_value_ids -= ptav

        vals = {}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals["product_uom"] = self.product_id.uom_id
            vals["product_uom_qty"] = self.product_uom_qty or 1.0

        product = self.product_id.with_context(
            lang=get_lang(self.env, self.order_id.partner_id.lang).code,
            partner=self.order_id.partner_id,
            quantity=vals.get("product_uom_qty") or self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id,
        )
        name = self.order_line_id.get_sale_order_line_multiline_description_sale(
            product
        )
        vals.update(name=self._get_product_descripation() or name)

        self._compute_tax_id()

        if self.order_id.pricelist_id and self.order_id.partner_id:
            vals["price_unit"] = self.env[
                "account.tax"
            ]._fix_tax_included_price_company(
                self._get_display_price(product),
                product.taxes_id,
                self.tax_id,
                self.company_id,
            )
        self.update(vals)
        self.purchase_price = self._compute_margin(
            self.order_id, self.product_id, self.product_uom
        )
        title = False
        message = False
        result = {}
        warning = {}
        if product.sale_line_warn != "no-message":
            title = _("Warning for %s") % product.name
            message = product.sale_line_warn_msg
            warning["title"] = title
            warning["message"] = message
            result = {"warning": warning}
            if product.sale_line_warn == "block":
                self.product_id = False
        return result

    @api.onchange("product_uom", "product_uom_qty")
    def product_uom_change(self):
        if not self.product_uom or not self.product_id:
            self.price_unit = 0.0
            return
        if self.order_id.pricelist_id and self.order_id.partner_id:
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner=self.order_id.partner_id,
                quantity=self.product_uom_qty,
                date=self.order_id.date_order,
                pricelist=self.order_id.pricelist_id.id,
                uom=self.product_uom.id,
                fiscal_position=self.env.context.get("fiscal_position"),
            )
            self.price_unit = self.env["account.tax"]._fix_tax_included_price_company(
                self._get_display_price(product),
                product.taxes_id,
                self.tax_id,
                self.company_id,
            )


class AccountMove(models.Model):
    _inherit = "account.move"
    _description = "Account Move"

    package_id = fields.Many2one(
        "sale.order.template", "Package", domain=[("is_package", "=", True)]
    )
    passenger_ids = fields.One2many("travellers.list", "invoice_id", "Passenger")
