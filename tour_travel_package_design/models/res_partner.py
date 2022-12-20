# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'
    partner_type = fields.Selection([('direct', "Direct"),
                                     ('indirect', 'Indirect'),
                                     ('agent', 'Agent'),
                                     ('sub_agent', 'Sub Agent')],
                                    default='direct', string="Type")

    @api.model
    def name_create(self, name):
        """
        Override name_create method to assign category of passenger
        and type of contact.
        """
        res = super(ResPartner, self).name_create(name)
        if self._context.get('passenger'):
            p_categ_id = self.env['res.partner.category'].search(
                [('name', 'in', ['Passenger', 'passenger'])], limit=1)
            if p_categ_id:
                categ_id = p_categ_id
            else:
                categ_id = self.env['res.partner.category'].create(
                    {'name': 'Passenger'})
            partner_id = self.browse(res[0])
            partner_id.category_id = [categ_id.id]
            partner_id.type = 'contact'
        return res


class VehicalRates(models.Model):

    _name = 'vehical.rates'
    _description = 'Vehical Rates'

    vehicle_id = fields.Many2one('product.product', "Product")
    duration_from = fields.Float('Duration From')
    duration_to = fields.Float('Duration To')
    extra_hours_rate = fields.Float('Extra Hours(Rate)')
    services = fields.Selection([('half_day', 'Half Day Use'),
                                 ('full_day', 'Full Day Use'),
                                 ('other', 'Other Excursions'),
                                 ('airport', 'Airport Pickup & Drop off')],
                                default='half_day')
    vehicle_contract_id = fields.Many2one('hr.contract', 'Contract')
    rate = fields.Float('Rate')

    @api.model
    def create(self, vals):
        """Override create method to update vender of product."""
        res = super(VehicalRates, self).create(vals)
        if res.vehicle_contract_id:
            supplier_vals = {'product_id': res.vehicle_id.id or False,
                             'name': res.vehicle_contract_id.
                             partner_id.id or False,
                             'price': res.rate}
            res.vehicle_id.seller_ids = [(0, 0, supplier_vals)]
        return res


class RateCards(models.Model):

    _name = 'rate.cards'
    _description = 'Rate Cards'

    name = fields.Char("Name")
    hotel_id = fields.Many2one('product.product', "Hotel")
    contract_id = fields.Many2one('hr.contract', 'Contract ',
                                  ondelete="cascade")
    season_ids = fields.One2many('resource.calendar.attendance', 'card_id',
                                 String="Season")
    meal_supplement_ids = fields.One2many('meal.supplement', 'meal_rate_id',
                                          'Meal Supplement')
    hotel_contract_id = fields.Many2one('hotel.contract', "Hotel Contract")

    @api.model
    def create(self, vals):
        """Override create method to update vender of product."""
        res = super(RateCards, self).create(vals)
        if res.contract_id:
            supplier_vals = {'product_id': res.hotel_id.id,
                             'name': res.contract_id.partner_id.id,
                             }
            res.hotel_id.seller_ids = [(0, 0, supplier_vals)]
        return res


class Contract(models.Model):

    _inherit = 'hr.contract'

    @api.constrains('date_start', 'date_end')
    def _check_date(self):
        """Contract should not be overlap with same dates and type."""
        for contract in self:
            domain = [
                ('date_start', '<=', contract.date_end),
                ('date_end', '>=', contract.date_start),
                ('partner_id', '=', contract.partner_id.id),
                ('id', '!=', contract.id),
                ('contract_type', '=', contract.contract_type)
            ]
            contract_ids = self.search(domain, count=True)
            if contract_ids:
                raise ValidationError(_('You can not have 2 \
                                contract that overlaps on same date!'))
        return True

    @api.model
    def create(self, vals):
        """
        Override create method to check weather current logged in user has
        contract Approver group then state in Running state else New state.
        """
        grp_name = 'tour_travel_package_design.group_contract_approver'
        res = super(Contract, self).create(vals)
        res.type_id_onchange()
        user = self.env['res.users'].browse(self.env.user).has_group(grp_name)
        if user:
            res.state = 'open'
        return res

    @api.multi
    def unlink(self):
        """Method for not to delete contract in running state."""
        for rec in self:
            if rec.state == 'open':
                raise ValidationError(
                    _("You can't delete contract in running state"))
            return super(Contract, self).unlink()

    notes = fields.Text('Notes')
    vehicle_rate_ids = fields.One2many('vehical.rates', 'vehicle_contract_id',
                                       String="Rate Cards")
    rate_ids = fields.One2many('rate.cards', 'contract_id',
                               String="Rate Cards")
    employee_id = fields.Many2one('hr.employee',
                                  string='Employee',
                                  required=False)
    partner_id = fields.Many2one('res.partner', 'Supplier')
    vehicle_type_id = fields.Many2one('vehicle.details',
                                      'Vehicle Type')
    hotel_id = fields.Many2one('product.product',
                               "Hotel Name")
    duration_from = fields.Char('Duration from')
    duration_to = fields.Float('Duration to')
    extra_hours_rate = fields.Float('Extra Hours(Rate)')
    services = fields.Selection([('half_day', 'Half Day Use'),
                                 ('full_day', 'Full Day Use'),
                                 ('other', 'Other Excursions'),
                                 ('airport', 'Airport Pickup & Drop off')],
                                default='half_day')
    contract_type = fields.Char("Contract Type")
    guide_contract_ids = fields.One2many('meal.contract', 'guide_contract_id',
                                         string="Guide")
    ticket_contract_ids = fields.One2many('meal.contract',
                                          'ticket_contract_id',
                                          string="Ticket")
    meal_contract_ids1 = fields.One2many('meal.contract',
                                         'meal_contract_id1', string="Meal")
    tour_contract_ids = fields.One2many('meal.contract', 'tour_contract_id',
                                        string="Tour")
    visa_contract_ids = fields.One2many('meal.contract', 'visa_contract_id',
                                        string="Visa")
    other_contract_ids = fields.One2many('meal.contract', 'other_contract_id',
                                         string="Other")
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  default=lambda self: self.env.user.
                                  company_id.currency_id)

    @api.onchange('type_id')
    def type_id_onchange(self):
        """Set the contract type for relevant contract."""
        for rec in self:
            if rec.type_id.type == "hotel":
                rec.contract_type = "hotel"
            elif rec.type_id.type == "transportation":
                rec.contract_type = "transportation"
            elif rec.type_id.type == "meal":
                rec.contract_type = "meal"
            elif rec.type_id.type == "guide":
                rec.contract_type = "guide"
            elif rec.type_id.type == "ticket":
                rec.contract_type = "ticket"
            elif rec.type_id.type == "tour":
                rec.contract_type = "tour"
            elif rec.type_id.type == "other":
                rec.contract_type = "other"
            elif rec.type_id.type == "visa":
                rec.contract_type = "visa"
            else:
                rec.contract_type = False


class MealContract(models.Model):
    _name = 'meal.contract'
    _description = 'Meal Contract'

    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Char('Description')
    price_unit = fields.Float("Price")
    guide_contract_id = fields.Many2one('hr.contract', 'Guide Contract',
                                        copy=False)
    meal_contract_id1 = fields.Many2one('hr.contract', 'Meal Contract',
                                        copy=False)
    ticket_contract_id = fields.Many2one('hr.contract', 'Ticket Contract',
                                         copy=False)
    tour_contract_id = fields.Many2one('hr.contract', 'Tour Contract',
                                       copy=False)
    visa_contract_id = fields.Many2one('hr.contract', 'Visa Contract',
                                       copy=False)
    other_contract_id = fields.Many2one('hr.contract', 'Other Contract',
                                        copy=False)
    days_valid_ids = fields.Many2many('days.valid', 'meal_days_rel',
                                      'meal_ids', 'days_id', 'Days Valid')
    menu_type_ids = fields.Many2many('meal.menu', string="Menu Type")
    restaurant_id = fields.Many2one('res.partner', string="Restaurant")

    @api.model
    def create(self, vals):
        """Override create method to update vender of product."""
        res = super(MealContract, self).create(vals)
        contract_id = False
        meal_contract_id = res.meal_contract_id1
        guide_contract_id = res.guide_contract_id
        ticket_contract_id = res.ticket_contract_id
        visa_contract_id = res.visa_contract_id
        tour_contract_id = res.tour_contract_id
        other_contract_id = res.other_contract_id
        if other_contract_id:
            contract_id = other_contract_id
        if tour_contract_id:
            contract_id = tour_contract_id
        if visa_contract_id:
            contract_id = visa_contract_id
        if ticket_contract_id:
            contract_id = ticket_contract_id
        if meal_contract_id:
            contract_id = meal_contract_id
        if guide_contract_id:
            contract_id = guide_contract_id
        if contract_id:
            supplier_vals = {'product_id': res.product_id.id or False,
                             'name': contract_id.partner_id.id or False,
                             'price': res.price_unit}
            res.product_id.seller_ids = [(0, 0, supplier_vals)]
        return res


class ContractType(models.Model):

    _inherit = 'hr.contract.type'

    type = fields.Selection([('transportation', 'Transportation'),
                             ('meal', 'Meal'), ('hotel', 'Hotel'),
                             ('ticket', 'Ticket'),
                             ('tour', 'Tour'),
                             ('visa', 'Visa'),
                             ('guide', 'Guide'),
                             ('other', 'Other')],
                            default='other')
