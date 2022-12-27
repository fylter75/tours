# See LICENSE file for full copyright and licensing details.
from datetime import datetime

import werkzeug.utils

from odoo import http
from odoo.http import request

from odoo.addons.website.controllers.main import Website


class QueryURL(object):
    def __init__(self, path="", **args):
        self.path = path
        self.args = args

    def __call__(self, path=None, **kw):
        if not path:
            path = self.path
        for k, v in self.args.items():
            kw.setdefault(k, v)
        lst = []
        for k, v in kw.items():
            if v:
                if isinstance(v, list) or isinstance(v, set):
                    lst.append(werkzeug.url_encode([(k, i) for i in v]))
                else:
                    lst.append(werkzeug.url_encode([(k, v)]))
        if lst:
            path += "?" + "&".join(lst)
        return path


class WebsiteHomepage(Website):
    @http.route()
    def index(self, **kw):
        domain = [("website_published", "=", True)]
        packages = request.env["package.category"].search(domain)
        testimonials = (
            request.env["testimonial.testimonial"]
            .sudo()
            .search(domain, order="sequence asc")
        )
        return request.render(
            "website.homepage", {"testimonials": testimonials, "packages": packages}
        )


class WebsiteTours(http.Controller):
    @http.route(["/packages"], type="http", auth="public", website=True)
    def packages(self, search="", page=0, **kwargs):
        attrib_list = request.httprequest.args.getlist("categories")
        attrib_values = [map(int, v.split("-")) for v in attrib_list if v]

        attrib_ids = [set(v) for v in attrib_values]

        attrib_set1 = list(attrib_ids)
        attrib_set = [list(i)[0] for i in attrib_set1]
        keep = QueryURL("/")
        domain = [
            ("state", "=", "confirm"),
            ("category_id.website_published", "=", True),
        ]
        package_categ = request.env["package.category"].search(
            [("website_published", "=", True)]
        )
        if search:
            kwargs["search"] = search
            search = kwargs["search"]
            domain += [("name", "ilike", search)]
        if attrib_set:
            domain += [("category_id", "in", attrib_set)]
        packages = request.env["sale.order.template"].search(
            domain, order="write_date desc"
        )
        return request.render(
            "website_tour_agency.packages",
            {
                "keep": keep,
                "search": search,
                "package_categs": package_categ,
                "categs_selected": attrib_set,
                "packages": packages,
            },
        )

    @http.route(["/hotels"], type="http", auth="public", website=True)
    def hotels(self, search="", page=0, star=0, **kwargs):
        attrib_list = request.httprequest.args.getlist("facilities")
        attrib_values = [map(int, v.split("-")) for v in attrib_list if v]

        attrib_ids = [set(v) for v in attrib_values]

        attrib_set1 = list(attrib_ids)
        attrib_set = [list(i)[0] for i in attrib_set1]

        keep = QueryURL("/")
        domain = [
            ("registration_type", "=", "hotel"),
            ("is_hotel", "=", True),
            ("website_visible", "=", True),
        ]
        # url = "/hotels"

        if search:
            kwargs["search"] = search
            search = kwargs["search"]
            domain += [
                ("name", "ilike", search),
            ]
            hotels = request.env["res.partner"].search(domain)

        if star:
            kwargs["star"] = star
            star = kwargs["star"]
            domain += [("rating", "ilike", star)]

        if attrib_set:
            for att in attrib_set:
                domain += [
                    ("facilities_ids", "in", attrib_set),
                    ("facilities_ids", "in", att),
                ]

        hotels = request.env["res.partner"].sudo().search(domain)
        facilities = request.env["hotel.facilities"].search([])
        return request.render(
            "website_tour_agency.hotel",
            {
                "keep": keep,
                "search": search,
                "hotels": hotels,
                "star": star,
                "facilities": facilities,
                "facilities_selected": attrib_set,
            },
        )

    @http.route(
        ["""/hotel/details/<int:partner_id>"""],
        type="http",
        auth="public",
        website=True,
    )
    def hotel_details_view(self, partner_id=0, **post):
        values = {
            "countries": request.env["res.country"].sudo().search([]),
            "company": request.env["res.company"].sudo().search([]),
        }
        if partner_id:
            hotel = (
                request.env["res.partner"]
                .sudo()
                .search(
                    [
                        ("id", "=", partner_id),
                        ("registration_type", "=", "hotel"),
                        ("is_hotel", "=", True),
                        ("website_visible", "=", True),
                    ]
                )
            )
            if hotel:
                values.update({"template": hotel})
        return request.render("website_tour_agency.hotel_details_page", values)

    @http.route(
        ["/hotel/details/<int:partner_id>/inquiry"],
        type="http",
        auth="public",
        website=True,
    )
    def hotel_inquiry(self, partner_id=0, **post):
        values = {
            "countries": request.env["res.country"].sudo().search([]),
            "company": request.env["res.company"].sudo().search([]),
        }
        if partner_id:
            hotel = (
                request.env["res.partner"]
                .sudo()
                .search(
                    [
                        ("id", "=", partner_id),
                        ("registration_type", "=", "hotel"),
                        ("is_hotel", "=", True),
                        ("website_visible", "=", True),
                    ]
                )
            )
            if hotel:
                values.update({"hotel": hotel})
        return request.render("website_tour_agency.hotel_inquiry", values)

    @http.route(
        ["/package/details/<model('sale.order.template'):order>"],
        type="http",
        auth="public",
        website=True,
    )
    def package_details_view(self, order, **post):
        values = {
            "template": order,
            "countries": request.env["res.country"].sudo().search([]),
            "company": request.env["res.company"].sudo().search([]),
        }
        return request.render("website_tour_agency.package_details", values)

    @http.route(
        ["/package/details/<model('sale.order.template'):order>/inquiry"],
        type="http",
        auth="public",
        website=True,
    )
    def package_inquiry(self, order, **post):
        values = {
            "template": order,
            "countries": request.env["res.country"].sudo().search([]),
            "company": request.env["res.company"].sudo().search([]),
        }
        return request.render("website_tour_agency.package_inquiry", values)

    @http.route(["/visa/inquiry"], type="http", auth="public", website=True)
    def visa_inquiry(self, **post):
        domain = [("type_travel_product", "=", "visa")]
        visa_list = request.env["product.product"].sudo().search(domain)
        values = {
            "visas": visa_list,
            "countries": request.env["res.country"].sudo().search([]),
            "company": request.env["res.company"].sudo().search([]),
        }
        return request.render("website_tour_agency.visa_inquiry", values)

    @http.route(["/contactus_thanks_travel"], type="http", auth="public", website=True)
    def contact_us(self, **post):
        return request.render("website_tour_agency.contactus_thanks_travel")

    @http.route(["/visa"], type="http", auth="public", website=True)
    def get_visa(self, **post):
        return request.render("website_tour_agency.visa")

    @http.route(["/transportation"], type="http", auth="public", website=True)
    def get_trasportation(self, **post):
        val = {
            "countries": request.env["res.country"].sudo().search([]),
        }
        return request.render("website_tour_agency.transportation", val)

    @http.route(
        ["/submit_inquiry"], type="http", auth="public", website=True, csrf=False
    )
    def submit_inquiry(self, **post):
        if "csrf_token" in post:
            list(map(post.pop, ["csrf_token"]))
        if "date_of_arrival" in post and post.get("date_of_arrival"):
            start_dt = datetime.strptime(post.get("date_of_arrival"), "%m/%d/%Y").date()
            post.update({"date_of_arrival": start_dt})
        if "date_of_return" in post and post.get("date_of_return"):
            end_dt = datetime.strptime(post.get("date_of_return"), "%m/%d/%Y").date()
            post.update({"date_of_return": end_dt})
        lead = request.env["crm.lead"].sudo().create(post)
        template = request.env.ref("website_tour_agency.client_inquiry")
        template.sudo().send_mail(lead.id, force_send=True)
        return request.redirect("/contactus_thanks_travel")
