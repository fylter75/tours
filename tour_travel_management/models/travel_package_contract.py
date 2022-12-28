#  See LICENSE file for full copyright and licensing details.
import datetime

from dateutil import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PackageContract(models.Model):
    _name = "package.contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Package Contract"

    name = fields.Char("Contract", required=True)
    partner_id = fields.Many2one("res.partner", "Supplier")
    date_start = fields.Date("Start Date", help="Contract start date")
    date_end = fields.Date("End Date", help="Contract end date")
    currency_id = fields.Many2one("res.currency", "Currency")
    company_id = fields.Many2one(
        "res.company", "company", default=lambda self: self.env.company
    )
    state = fields.Selection(
        [
            ("draft", "New"),
            ("open", "Running"),
            ("close", "Expired"),
            ("cancel", "Cancelled"),
        ],
        "Status",
        help="Status of the contract",
        default="draft",
    )
    notes = fields.Text("Notes")
    package_contract_type = fields.Selection([], "Type")
    seasons_ids = fields.Many2many("travelling.season", string="Season")
    city_id = fields.Many2one("city.city", "City")
    cancel_reason_id = fields.Many2one("package.contract.cancel", "Cancel Reason")

    def button_start(self):
        self.write({"state": "open"})

    def button_close(self):
        self.write({"state": "close"})

    def button_set_to_renew(self):
        date_start = self.date_end + datetime.timedelta(days=1)
        date_end = date_start + relativedelta.relativedelta(months=1)
        default = {"date_start": date_start, "date_end": date_end}
        new_package_contract_id = self.copy(default).id
        return {
            "type": "ir.actions.act_window",
            "res_model": "package.contract",
            "view_type": "form",
            "view_mode": "form",
            "target": "current",
            "res_id": new_package_contract_id,
            "flags": {"form": {"action_buttons": True, "options": {"mode": "edit"}}},
        }

    @api.constrains("date_start", "date_end", "partner_id", "package_contract_type")
    def _check_start_end_date(self):
        """
        Contract should not be overlap with same dates and type.
        """
        for contract in self:
            contract_count = self.search_count(
                [
                    ("date_start", "<=", contract.date_end),
                    ("date_end", ">=", contract.date_start),
                    ("partner_id", "=", contract.partner_id.id),
                    ("id", "!=", contract.id),
                    ("package_contract_type", "=", contract.package_contract_type),
                    ("state", "!=", "cancel"),
                ]
            )
            if contract_count:
                raise ValidationError(
                    _(
                        """You can not have 2 contract that """
                        """overlaps on same date!"""
                    )
                )
            if contract.date_start and contract.date_end:
                if contract.date_start < fields.Date.context_today(self):
                    raise ValidationError(
                        _("""Please Enter valid contract duration.""")
                    )
                if contract.date_start > contract.date_end:
                    raise ValidationError(
                        _("""Please Enter valid contract duration.""")
                    )

        return True

    def unlink(self):
        """
        Method for not to delete contract in running state.
        """
        for contract in self:
            if contract.state in ["open", "close", "cancel"]:
                raise ValidationError(_("You can delete only new contracts."))
        return super(PackageContract, self).unlink()

    def _cron_7_day_before_email_reminder(self):
        day_7_before_date = fields.Date.context_today(self) - datetime.timedelta(days=7)
        contracts = self.search(
            [("date_end", "=", day_7_before_date), ("state", "in", ["open"])]
        )
        template = self.env.ref("tour_travel_management.email_template_7_day_before")
        for contract in contracts:
            template.send_mail(contract.id, force_send=True)

    def _cron_auto_expiry(self):
        current_date = fields.Date.context_today(self)
        contracts = self.search(
            [("date_end", "=", current_date), ("state", "in", ["open"])]
        )
        template = self.env.ref(
            "tour_travel_management.email_template_expire_package_contract"
        )
        for contract in contracts:
            template.send_mail(contract.id, force_send=True)
            contract.write({"state": "close"})

    def send_contract_receipt_mail(self):
        """
        This function opens a window to compose an email,
        template message loaded by default.
        @param self: object pointer
        """
        assert len(self._ids) == 1, "This is for a single id at a time."
        ir_model_data = self.env["ir.model.data"]
        try:
            template_id = self.env.ref(
                "tour_travel_management.mail_template_package_contract_receipt"
            ).id
        except ValueError:
            template_id = False
        try:
            compose_form_id = self.env.ref('mail.email_compose_message_wizard_form').id
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update(
            {
                "default_model": "package.contract",
                "default_res_id": self._ids[0],
                "default_use_template": bool(template_id),
                "default_template_id": template_id,
                "default_composition_mode": "comment",
                "force_send": True,
                "mark_so_as_sent": True,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(compose_form_id, "form")],
            "view_id": compose_form_id,
            "target": "new",
            "context": ctx,
            "force_send": True,
        }

    @api.onchange("city_id", "package_contract_type")
    def _onchange_city_id(self):
        "Inherited in other process"
        pass


class PackageContractDetails(models.Model):
    _name = "package.contract.details"
    _description = "Package Contract Details"

    product_id = fields.Many2one("product.product", "Product")
    hours = fields.Float("Hours")
    rate = fields.Float("Rate")
    extra_hour = fields.Float("Extra Hours(Rate)")
    services = fields.Selection(
        [
            ("half_day", "Half Day Use"),
            ("full_day", "Full Day Use"),
            ("other", "Other Excursions"),
            ("airport", "Airport Pickup & Drop off"),
        ],
        string="Services",
        default="half_day",
    )
    description = fields.Char("Description")
    restaurant_id = fields.Many2one("res.partner", "Restaurant")
    price = fields.Float("Price")
    package_contract_id = fields.Many2one("package.contract", "Package Contract")
    type_travel_product = fields.Selection(
        [
            ("hotel", "Hotel"),
            ("transportation", "Transportation"),
            ("tickets", "Tickets"),
            ("ticketing", "Ticketing"),
            ("tour", "Tour"),
            ("meals", "Meals"),
            ("visa", "Visa"),
            ("guide", "Guide"),
            ("other", "Other"),
        ],
        string="Type",
    )


class PackageContractCancel(models.Model):
    _name = "package.contract.cancel"
    _description = "Package Contract Cancel"

    name = fields.Char("Cancel Reason")


class PackageContractLine(models.Model):
    _name = "package.contract.line"
    _description = "Package Contract Line"

    name = fields.Char("Cancel Reason")
