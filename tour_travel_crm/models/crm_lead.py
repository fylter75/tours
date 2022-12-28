#  See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class Lead(models.Model):
    _inherit = "crm.lead"

    @api.depends("date_of_arrival", "date_of_return")
    def _compute_no_days(self):
        for rec in self:
            if rec.date_of_arrival and rec.date_of_return:
                rec.stay_duration = (rec.date_of_return - rec.date_of_arrival).days
            else:
                rec.stay_duration = 0

    date_of_arrival = fields.Date("Date of Arrival")
    date_of_return = fields.Date("Date of Return")
    adult = fields.Integer("No of Adults", default=1)
    children = fields.Integer("No of Children")
    package_id = fields.Many2one(
        "sale.order.template", string="Package", ondelete="restrict"
    )
    stay_duration = fields.Integer(
        compute="_compute_no_days",
        string="Duration of Stay",
        copy=False,
        readonly=True,
        store=True,
        tracking=True,
    )
    meal_type = fields.Selection(
        [("veg", "Veg"), ("nonveg", "Non Veg")], string="Meal Type", default="veg"
    )
    transportation_id = fields.Many2one("transportation.mode", "Transportation Mode")
    hotel_id = fields.Many2one("hotel.type", "Hotel Type")
    assistanece_required = fields.Boolean("Yes")
    assistanece_not_required = fields.Boolean("No")
    visa_assistance = fields.Selection(
        [("yes", "Yes"), ("no", " No")],
        string="Is Visa Assistance Required",
        default="no",
    )
    applied_country_id = fields.Many2one("res.country", "Applied Visa For")
    visa_id = fields.Many2one("product.product", "Visa Type", ondelete="restrict")
    passport_number = fields.Char("Passport Number")
    name_on_passport = fields.Char("Name on Passport")
    purpose_to_visit_id = fields.Many2one(
        "visit.purpose", "Purpose to Visit", ondelete="restrict"
    )
    visiting_location_ids = fields.One2many(
        "visiting.location", "lead_id", "Visiting Location Information"
    )
    tour_type = fields.Selection(
        [("domestic", "Domestic"), ("international", "International")],
        string="Tour Type",
        default="domestic",
    )

    def action_new_quotation(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "tour_travel_crm.sale_action_quotations_new"
        )
        action["context"] = {
            "search_default_opportunity_id": self.id,
            "default_opportunity_id": self.id,
            "search_default_partner_id": self.partner_id.id,
            "default_partner_id": self.partner_id.id,
            "default_team_id": self.team_id.id,
            "default_campaign_id": self.campaign_id.id,
            "default_medium_id": self.medium_id.id,
            "default_origin": self.name,
            "default_source_id": self.source_id.id,
            "default_company_id": self.company_id.id or self.env.company.id,
            "default_tag_ids": self.tag_ids.ids,
            "default_sale_order_template_id": self.package_id.id,
            "default_is_registration": True,
        }
        return action

    def action_view_sale_quotation(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "tour_travel_management.tour_package_registration_quotations"
        )
        action["context"] = {
            "search_default_draft": 1,
            "search_default_partner_id": self.partner_id.id,
            "default_partner_id": self.partner_id.id,
            "default_opportunity_id": self.id,
            "default_is_registration": True,
        }
        action["domain"] = [
            ("opportunity_id", "=", self.id),
            ("state", "in", ["draft", "sent"]),
        ]
        quotations = self.mapped("order_ids").filtered(
            lambda l: l.state in ("draft", "sent")
        )
        if len(quotations) == 1:
            action["views"] = [
                (
                    self.env.ref(
                        "tour_travel_management.tour_package_registration_form"
                    ).id,
                    "form",
                )
            ]
            action["res_id"] = quotations.id
        return action


class VisitPurpose(models.Model):
    _name = "visit.purpose"
    _description = "Visiting Purpose"

    name = fields.Char("Purpose of Visit", required=True)


class VisitingLocation(models.Model):
    _name = "visiting.location"
    _description = "Visiting Location"

    name = fields.Char("Visit Location", required=True)
    city_id = fields.Many2one("city.city", "City")
    state_id = fields.Many2one("res.country.state", "State")
    country_id = fields.Many2one(
        "res.country",
        "Country",
        default=lambda self: self.env.user.company_id.country_id,
        required=True,
    )
    lead_id = fields.Many2one("crm.lead", "Lead")


class ModeOfTransportation(models.Model):
    _name = "transportation.mode"
    _description = "Mode of Transportation"

    name = fields.Char("Transportation Mode", required=True)


class TypeOfHotel(models.Model):
    _name = "hotel.type"
    _description = "Type of Hotel"

    name = fields.Char("Hotel Type", required=True)
