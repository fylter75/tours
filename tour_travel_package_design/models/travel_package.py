#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo import _, api, fields, models
import odoo.addons.decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import ValidationError, UserError


class Airport(models.Model):
    _name = 'airport'
    _description = 'Airport'

    name = fields.Char('Name')
    code = fields.Char('Code')


class PassengerList(models.Model):
    _name = 'passenger.list'
    _description = 'Passenger List'
    _rec_name = 'partner_id'
    _order = 'number'

    number = fields.Char('Sequence')
    room = fields.Char("Room")
    hotel_id = fields.Many2one('hotel.contract', "Hotel")
    room_type = fields.Char('Room Type')
    sequence = fields.Integer("Number")
    partner_id = fields.Many2one('res.partner', String="Name")
    age = fields.Integer('Age')
    gender = fields.Selection([('male', 'Male'),
                               ('female', 'Female'),
                               ('child', 'Child')], default='male')
    type = fields.Char('Remarks')
    country_id = fields.Many2one('res.country', 'Nationality of client')
    so_id = fields.Many2one('sale.order',
                            index=True, copy=False)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def name_create(self, name):
        """
        Override name_create method to assign category of
        relative product creation.
         ---------------------------------
        @param self : object pointer
        """
        res = super(ProductProduct, self).name_create(name)
        parent_id = self.env['product.category'].\
            search([('parent_id.name', '=', 'All')], limit=1)
        product_id = self.browse(res[0])
        if self._context.get('hotel_onchange'):
            categ_id = self.env['product.category'].\
                search(['|', ('parent_id.name', '=', 'Hotel'),
                        ('name', '=', 'Hotel')], limit=1)
            if categ_id:
                parent_id = categ_id.id
            else:
                parent_id = self.env['product.category'].create(
                    {'name': 'Hotel'}).id
        elif self._context.get('vehicle'):
            categ_id = self.env['product.category'].\
                search(['|', ('parent_id.name', '=', 'Transportation'),
                        ('name', '=', 'Transportation')], limit=1)
            if categ_id:
                parent_id = categ_id.id
            else:
                parent_id = self.env['product.category'].create(
                    {'name': 'Transportation'}).id
        elif self._context.get('ticket'):
            categ_id = self.env['product.category'].\
                search(['|', ('parent_id.name', '=', 'Ticket'),
                        ('name', '=', 'Ticket')], limit=1)
            if categ_id:
                parent_id = categ_id.id
            else:
                parent_id = self.env['product.category'].create(
                    {'name': 'Ticket'}).id
        elif self._context.get('meal'):
            categ_id = self.env['product.category'].\
                search(['|', ('parent_id.name', '=', 'Meals'),
                        ('name', '=', 'Meals')], limit=1)
            if categ_id:
                parent_id = categ_id.id
            else:
                parent_id = self.env['product.category'].create(
                    {'name': 'Meals'}).id
        elif self._context.get('guide'):
            categ_id = self.env['product.category'].\
                search(['|', ('parent_id.name', '=', 'Guides'),
                        ('name', '=', 'Guides')], limit=1)
            if categ_id:
                parent_id = categ_id.id
            else:
                parent_id = self.env['product.category'].create(
                    {'name': 'Guides'}).id
        elif self._context.get('ticketing'):
            categ_id = self.env['product.category'].\
                search(['|', ('parent_id.name', '=', 'Ticketing'),
                        ('name', '=', 'Ticketing')], limit=1)
            if categ_id:
                parent_id = categ_id.id
            else:
                parent_id = self.env['product.category'].create(
                    {'name': 'Ticketing'}).id
        elif self._context.get('visa'):
            categ_id = self.env['product.category'].\
                search(['|', ('parent_id.name', '=', 'Visa'),
                        ('name', '=', 'Visa')], limit=1)
            if categ_id:
                parent_id = categ_id.id
            else:
                parent_id = self.env['product.category'].create(
                    {'name': 'Visa'}).id
        elif self._context.get('tour'):
            categ_id = self.env['product.category'].\
                search(['|', ('parent_id.name', '=', 'Tour'),
                        ('name', '=', 'Tour')], limit=1)
            if categ_id:
                parent_id = categ_id.id
            else:
                parent_id = self.env['product.category'].create(
                    {'name': 'Tour'}).id
        product_id.categ_id = parent_id
        return res


class HotelContract(models.Model):

    _name = 'hotel.contract'
    _description = 'Hotel Contract'

    _rec_name = 'hotel_id'

    @api.onchange('room_accupacy_id')
    def onchange_accupacy(self):
        '''
        set the number of person in Hotel as per configured.
        ---------------------------------
        @param self : object pointer
        '''
        for rec in self:
            if rec.room_accupacy_id:
                rec.no_of_person = rec.room_accupacy_id.no_of_person
                rec.room_type = False

    @api.multi
    @api.depends('product_uom_qty', 'price_unit', 'room_qty')
    def _compute_rate(self):
        '''
        compute the subtotal as per number of room quantity, uom
        and unit price.
        ---------------------------------
        @param self : object pointer
        '''

        for rec in self:
            rec.price_subtotal = rec.product_uom_qty * rec.price_unit * rec.\
                room_qty

    @api.onchange('from_date', 'to_date', 'room_accupacy_id', 'room_type')
    def onchange_date(self):
        '''
        Show contract that fall in defined date.
        ---------------------------------
        @param self : object pointer
        '''
        start_date = ''
        end_date = ''
        contract_obj = self.env['hr.contract']
        calendar_obj = self.env['resource.calendar.attendance']
        res = {'domain': {}}
        if self.from_date or self.to_date:
            if self.partner_id:
                contract_id = contract_obj.search(
                    [('state', '=', 'open'),
                     ('partner_id', '=', self.partner_id.id),
                     ('contract_type', '=', 'hotel'),
                     ('date_start', '<=', self.sale_id.arrival_date),
                     ('date_end', '>=', self.sale_id.arrival_date),
                     ('date_start', '<=', self.sale_id.return_date),
                     ('date_end', '>=', self.sale_id.return_date)
                     ])
                if not contract_id:
                    raise ValidationError(_('No season contract for this period \
                    %s and %s') % (self.sale_id.arrival_date,
                                   self.sale_id.return_date))

                if contract_id:
                    for contract_rec in contract_id.rate_ids:
                        if self.hotel_id.id == contract_rec.hotel_id.id:
                            if self.from_date and self.to_date:
                                if self.to_date:
                                    if self.to_date.hotel_date < self.from_date.hotel_date:
                                        raise UserError(
                                            _('To date must be greater than from date'))
                                cal_ids = calendar_obj.search(
                                    [('card_id', '=', contract_rec.id),
                                     ('date_from', '<=',
                                      self.from_date.hotel_date),
                                     ('date_to', '>=',
                                      self.from_date.hotel_date),
                                     ('date_from', '<=',
                                      self.to_date.hotel_date),
                                     ('date_to', '>=',
                                      self.to_date.hotel_date), ])
                                if not cal_ids:
                                    raise ValidationError(_('No season \
                                    available for this period %s and \
                                    %s') % (self.from_date.hotel_date,
                                            self.to_date.hotel_date))
                                if cal_ids:
                                    rm_list = []
                                    self.price_unit = 0.0
                                    # if not self.room_type:
                                    #     self.room_type = cal_ids[0].room_type
                                    if not self.room_accupacy_id:
                                        self.room_accupacy_id = \
                                            cal_ids[0].room_selection_id.id
                                    for cal_rec in cal_ids:
                                        if cal_rec.room_selection_id.id == \
                                                self.room_accupacy_id.id:
                                            self.season_id = cal_rec.id
                                            rm_list.append(
                                                cal_rec.room_type.id)
                                            if cal_rec.room_type.id == \
                                                    self.room_type.id:
                                                if self.room_accupacy_id and \
                                                        self._context.get(
                                                            'room_type'):
                                                    self.price_unit = cal_rec.\
                                                        rate
                                            # if self.room_accupacy_id and not \
                                            #         self._context.get(
                                            #             'room_type'):
                                            #     self.price_unit = cal_rec.rate
                                                # self.room_type = cal_rec.\
                                                #     room_type
                                    res.update({'domain':
                                                {'season_id':
                                                 [('id', 'in', cal_ids.ids)]}})
                                    if cal_rec.room_selection_id.id == self.room_accupacy_id.id:

                                        res.update({'domain':
                                                    {'room_type':
                                                     [('id', 'in', rm_list)]}})
                                    else:
                                        res.update({'domain':
                                                    False})
            if self.from_date:
                str_strt_date = self.from_date.hotel_date.strftime('%Y-%m-%d')
                start_date = datetime.strptime(str_strt_date,
                                               DEFAULT_SERVER_DATE_FORMAT)
            if self.to_date:
                str_end_date = self.to_date.hotel_date.strftime('%Y-%m-%d')
                end_date = datetime.strptime(str_end_date,
                                             DEFAULT_SERVER_DATE_FORMAT)
            if start_date and end_date:
                days = (end_date - start_date).days
                if days >= 0.0:
                    self.product_uom_qty = days
            return res

    @api.multi
    @api.onchange('partner_id', 'hotel_id')
    def onchange_partner_id(self):
        '''
        shows the supplier of selected hotel otherwise display all the
        supplier.
        ---------------------------------
        @param self : object pointer
        '''
        res = {'domain': {}}
        partner_obj = self.env['res.partner']
        sellers = []
        for rec in self:
            if self._context.get('params'):
                if self._context.get('hotel_onchange'):
                    rec.partner_id = False
                    rec.name = False
                    rec.season_id = False
                    rec.room_selection_id = False
                    rec.room_type = False
                    rec.price_unit = 0.0
                    rec.product_qty_uom = 0.0
                if not rec.hotel_id:
                    rec.name = False
                    supp_ids = partner_obj.search([('supplier', '=', True)])
                    res['domain'].update({'partner_id': [('id', 'in',
                                                          supp_ids.ids)]})
                if self.hotel_id:
                    sellers = [x.name.id for x in rec.hotel_id.seller_ids]
                    if res:
                        if sellers:
                            res['domain'].update({'partner_id': [('id', 'in',
                                                                  sellers)]})
                        else:
                            supp_ids = partner_obj.search([('supplier', '=',
                                                            True)])
                            res['domain'].update({'partner_id':
                                                  [('id', 'in',
                                                    supp_ids.ids)]})
        return res

    @api.onchange('hotel_categ')
    def onchange_hotel_categ(self):
        '''
        It will set all the value as False when the hotel category
        is not selected.
        ---------------------------------
        @param self : object pointer
        '''
        if not self.hotel_categ or self.hotel_categ:
            self.hotel_id = False
            self.name = False
            self.room_type = False
            self.room_rate = 0.0
            self.partner_id = False
            self.season_id = False
            self.from_date = False
            self.to_date = False
            self.price_unit = False
            self.extra_bed_price = False

    @api.multi
    def convert_to_rfq(self):
        '''
        It will generate the Purchase Order.
        ---------------------------------
        @param self : object pointer
        '''
        po_obj = self.env['purchase.order']
        picking_type_obj = self.env['stock.picking.type']
        for hotel_rec in self:
            picking_id = picking_type_obj.search([('code', '=', 'incoming')],
                                                 limit=1)
            if not picking_id:
                raise ValidationError(_('No Picking found'))
            po_vals = {'partner_id': hotel_rec.partner_id.id or False,
                       'date_order': datetime.now(),
                       'currency_id': hotel_rec.sale_id.currency_id.id or
                       False,
                       'picking_type_id': picking_id.id or False,
                       'sale_order_id': hotel_rec.sale_id.id or False,
                       'company_id': hotel_rec.sale_id.company_id.id or False,
                       'arrival_date': hotel_rec.sale_id.arrival_date or False,
                       'return_date': hotel_rec.sale_id.return_date or False,
                       }
            po_rec = po_obj.create(po_vals)
            po_lines = []
            for h_rec in hotel_rec.sale_id.hotel_ids:
                if hotel_rec.hotel_id.id == h_rec.hotel_id.id:
                    po_lines.append((0, 0, {
                                     'name': h_rec.hotel_id.name,
                                     'date_planned': datetime.now(),
                                     'product_qty': h_rec.product_uom_qty,
                                     'product_id': h_rec.hotel_id.id or False,
                                     'order_id': po_rec.id or False,
                                     'from_date':
                                     h_rec.from_date.hotel_date and
                                     h_rec.from_date.hotel_date or '',
                                     'to_date': h_rec.to_date.hotel_date and
                                     h_rec.to_date.hotel_date or '',
                                     'price_unit': h_rec.price_unit,
                                     'product_uom': h_rec.hotel_id.uom_id.id,
                                     'room_accupacy_id':
                                     h_rec.room_accupacy_id.id,
                                     'room_qty': h_rec.room_qty
                                     }))
            po_rec.order_line = po_lines
            action = self.env.ref('purchase.purchase_rfq').read()[0]
            action['domain'] = [('id', '=', po_rec.id)]
            action['res_id'] = po_rec.id
        return action

    contract_id = fields.Many2one('hr.contract', 'Contract')
    name = fields.Char('Hotel Name')
    hotel_id = fields.Many2one('product.product', 'Hotel')
    hotel_categ = fields.Many2one('product.category', "Category")
    room_type = fields.Many2one('room.type', 'Room Type')
    location = fields.Char('Location')
    booking_ref = fields.Char('Booking Ref')
    sale_id = fields.Many2one('sale.order', ondelete='cascade', index=True,
                              copy=False, required=False)
    date = fields.Date(string='Date')
    room_rate = fields.Float("Rate")
    third_supplement = fields.Float("Third Supplement")
    notes = fields.Text("Terms and Conditions")
    partner_id = fields.Many2one('res.partner', string="Supplier")
    hotel_rate_ids = fields.One2many('rate.cards', 'hotel_contract_id',
                                     String="Rate Cards")
    season_id = fields.Many2one('resource.calendar.attendance',
                                string="Available Season")
    season_ids = fields.One2many('resource.calendar.attendance',
                                 'hotel_season_id', String="Seasons")
    notes = fields.Text('Notes')
    price_unit = fields.Float('Unit Price',
                              digits=dp.get_precision('Product Price'),
                              default=0.0)
    product_uom_qty = fields.Float(string='Quantity',
                                   digits=dp.get_precision(
                                       'Product Unit of Measure'),
                                   default=1.0)
    price_subtotal = fields.Float(compute='_compute_rate',
                                  string='Subtotal', readonly=True,
                                  store=True)
    single_price = fields.Float('Single Price')
    extra_bed_price = fields.Float('Extra Bed')
    from_date = fields.Many2one('date.days', "From")
    to_date = fields.Many2one('date.days', "To")
    room_accupacy_id = fields.Many2one('room.room', "Room Accupacy")
    room_qty = fields.Integer("Room Qty", default=1)
    no_of_person = fields.Integer("No. of Person")


class RoomType(models.Model):

    _name = 'room.type'
    _description = 'Room Type'

    name = fields.Char('Name')


class RoomRoom(models.Model):

    _name = 'room.room'
    name = fields.Char('Name')
    _description = 'Rooms'

    no_of_person = fields.Integer('No of Person')
    room_selection = fields.Selection([('single', 'Single'),
                                       ('double', 'Double'),
                                       ('tpl', 'TPL')], default='single')


class ResourceCalendarAttendance(models.Model):
    _inherit = "resource.calendar.attendance"

    rate = fields.Float('Rate')
    name = fields.Selection([('high', 'High'), ('low', 'Low'),
                             ('peak', 'Peak')], default='high', string="Name")
    hour_from = fields.Float(string='Work from', required=False,
                             index=True, help="Start and End time of working.")
    hour_to = fields.Float(string='Work to', required=False)
    room_type = fields.Many2one('room.type', 'Room Type')
    card_id = fields.Many2one('rate.cards', 'Rate Card')
    third_supplement = fields.Char('3rd Person Supplement')
    allotment = fields.Char('Allotment')
    allotment_release = fields.Char('Allotment Release')
    calendar_id = fields.Many2one("resource.calendar",
                                  string="Resource's Calendar",
                                  required=False, ondelete='cascade')
    working_hours = fields.Many2one('resource.calendar', string='Season')
    hotel_season_id = fields.Many2one('hotel.contract', "Hotel Contract")
    room_selection_id = fields.Many2one('room.room', "Room")

    @api.onchange('date_from', 'date_to')
    def onchange_dates(self):
        """
        This method will Define a Start Date
        Greater to the End Date.
        ---------------------------------
        @param self : object pointer
        """
        if self.date_from and self.date_to:
            if self.date_to < self.date_from:
                raise ValidationError(_('Start Date must \
                be anterior to End Date'))


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    attendance_ids = fields.One2many(
        'resource.calendar.attendance', 'calendar_id', string='',
        copy=True)
    meal_supplement_ids = fields.One2many('meal.supplement',
                                          'meal_calendar_id',
                                          'Meal Supplement')


class MealSupplement(models.Model):
    _name = "meal.supplement"
    _description = 'MealSupplement'

    age_group = fields.Selection([('adult', 'Adult'), ('child', 'Child')],
                                 string='Age Group', default='adult')
    half_board = fields.Float("Half Board")
    full_board = fields.Float("Full Board")
    meal_calendar_id = fields.Many2one('resource.calendar', 'Calendar')
    meal_rate_id = fields.Many2one('rate.cards', 'Meal')


class VehicleDetails(models.Model):
    _name = 'vehicle.details'
    _description = 'Vehicle Details'

    name = fields.Char('Description')
    seat_capacity = fields.Float('Seat Capacity')
    vehical_model = fields.Char("Models")
    plate_no = fields.Char("Plate No")


class VisaStatus(models.Model):
    _name = 'visa.status'
    _description = 'Visa Status'

    name = fields.Char('Name')


class TourAirline(models.Model):
    _name = 'tour.airline'
    _description = 'Tour Airline'

    name = fields.Char('Airline')
    country_id = fields.Many2one('res.country', 'Country')


class MealMenu(models.Model):
    _name = 'meal.menu'
    _description = 'Meal Menu'

    name = fields.Char('Name')


class VisaAttachments(models.Model):

    _name = 'visa.attachments'
    _description = 'Visa Attachments'

    product_id = fields.Many2one('product.product', 'Product')
    visa_docs_id = fields.Many2one('visa.docs', 'Required Documents')


class VisaDetails(models.Model):

    _name = 'visa.detail'
    _description = 'Visa Details'

    @api.multi
    @api.onchange('visa_id')
    def onchange_visa_id(self):
        """
        It will fil the value of fields according to selected visa.

        ---------------------------------
        @param self : object pointer
        """
        for visa_rec in self:
            if visa_rec.visa_id:
                visa_rec.product_id = visa_rec.visa_id.product_id.id
                visa_rec.partner_id = visa_rec.visa_id.partner_id.id
                visa_rec.categ_id = visa_rec.visa_id.categ_id.id
                visa_rec.name = visa_rec.visa_id.name
                visa_rec.visa_status_id = visa_rec.visa_id.visa_status_id.id
                visa_rec.product_uom_qty = visa_rec.visa_id.product_uom_qty
                visa_rec.price_unit = visa_rec.visa_id.price_unit

    visa_id = fields.Many2one('visa.detail', ondelete='cascade',
                              string="Visa",
                              index=True, copy=False)
    name = fields.Char('Name')
    partner_id = fields.Many2one('res.partner', 'Supplier')
    categ_id = fields.Many2one('product.category', 'Category')
    product_id = fields.Many2one('product.product', "Product")
    visa_sale_id = fields.Many2one('sale.order')
    visa_status_id = fields.Many2one('visa.status', 'Visa Status')
    product_uom_qty = fields.Float(string='Quantity',
                                   digits=dp.get_precision(
                                       'Product Unit of Measure'),
                                   required=True, default=1.0)
    price_unit = fields.Float('Unit Price', required=True,
                              digits=dp.get_precision('Product Price'),
                              default=0.0)


class DateDays(models.Model):
    _name = 'date.days'
    _description = 'Date Days'

    name = fields.Char("From Date")
    sale_day_id = fields.Many2one('sale.order', 'Order')
    hotel_date = fields.Date("Hotel Date")


class VisaDocs(models.Model):

    _name = 'visa.docs'
    _description = 'Visa Docs'

    name = fields.Char('Documents')
