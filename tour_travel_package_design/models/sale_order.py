#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, DEFAULT_SERVER_DATE_FORMAT
import odoo.addons.decimal_precision as dp
from lxml import etree


class AccountInvoice(models.Model):

    _inherit = 'account.invoice'

    so_order_id = fields.Many2one('sale.order', "Sale Order")


class ProductFacility(models.Model):
    """Data model for Product facility."""

    _name = 'product.facility'
    _description = 'Product Facilities'

    name = fields.Char('Name')
    icon_class = fields.Char("Facilities Icon", default='fa fa-check-circle-o')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    visa_doc_ids = fields.One2many('visa.attachments', 'product_id',
                                   'Attachments')
    facility_ids = fields.Many2many('product.facility', string='Facilities')


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    _order = 'day_date'

    @api.model
    def default_get(self, fields):
        """
        Override default_get method to set default document type in visa.

        ---------------------------------
        @param fields : list of fields.
        """
        res = super(SaleOrderLine, self).default_get(fields)
        if self._context.get('default_line_type') == 'visa' or \
                self._context.get('field_parent') == 'visa_order_id':
            request_id = self.env.ref(
                'tour_travel_package_design.visa_status6')
            res.update({'visa_status_id': request_id.id})
        return res

    @api.multi
    def _prepare_invoice_line(self, qty):
        """
        Prepare the dict of values to create the new invoice line for a\
         sales order line.

        :param qty: float quantity to invoice
        """
        self.ensure_one()
        if self.product_id:
            account = self.product_id.property_account_income_id or\
                self.product_id.categ_id.property_account_income_categ_id
        else:
            journal_id = self.env['account.invoice']._default_journal()
            account = journal_id.default_credit_account_id
        fpos = self.order_id.fiscal_position_id or\
            self.order_id.partner_id.property_account_position_id
        if fpos:
            account = fpos.map_account(account)
        res = {
            'name': self.name or '',
            'sequence': self.sequence,
            'origin': self.order_id and self.order_id.name or '',
            'account_id': account.id or False,
            'price_unit': self.price_unit,
            'quantity': qty,
            'discount': self.discount,
            'uom_id': self.product_uom.id or False,
            'product_id': self.product_id.id or False,
            'layout_category_id': self.layout_category_id and
            self.layout_category_id.id or False,
            'invoice_line_tax_ids': [(6, 0, self.tax_id.ids)],
            'account_analytic_id': self.order_id.analytic_account_id.id,
            'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
        }
        return res

    @api.multi
    def invoice_line_create(self, invoice_id, qty):
        """Create an invoice line. The quantity to invoice can be
             positive (invoice) or negative (refund).
            :param invoice_id: integer
            :param qty: float quantity to invoice
            :returns recordset of account.invoice.line created
        """
        invoice_lines = self.env['account.invoice.line']
        precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        for line in self:
            if not float_is_zero(qty, precision_digits=precision):
                vals = line._prepare_invoice_line(qty=qty)
                vals.update({'invoice_id': invoice_id,
                             'sale_line_ids': [(6, 0, [line.id])]})
                invoice_lines |= self.env['account.invoice.line'].create(vals)
        return invoice_lines

    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        if not self.product_uom or not self.product_id:
            return
        if self.order_id.pricelist_id and self.order_id.partner_id:
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner=self.order_id.partner_id.id,
                quantity=self.product_uom_qty,
                date=self.order_id.date_order,
                pricelist=self.order_id.pricelist_id.id,
                uom=self.product_uom.id,
                fiscal_position=self.env.context.get('fiscal_position')
            )
            self.price_unit = self.env[
                'account.tax']._fix_tax_included_price_company(
                    self._get_display_price(product), product.taxes_id,
                    self.tax_id, self.company_id)

    @api.multi
    def get_contract(self, contract_type, partner_id, arrival_date,
                     return_date):
        """
        Method added for searching  contract from dates and partner
        @return: return record set of contract
        """
        contract_obj = self.env['hr.contract']
        for rec in self:
            domain = [('contract_type', '=', contract_type),
                      ('state', '=', 'open')]
            if partner_id:
                domain.append(('partner_id', '=', partner_id))
            if arrival_date:
                domain.append(('date_start', '<=',
                               arrival_date))
                domain.append(('date_end', '>=',
                               arrival_date))
            if return_date:
                domain.append(('date_start', '<=',
                               return_date))
                domain.append(('date_end', '>=',
                               return_date))
            contract_id = contract_obj.search(domain)
        return contract_id

    @api.multi
    def get_contacts(self, partner_id, p_type, categ_list):
        partner_obj = self.env['res.partner']
        p_ids = []
        for rec in self:
            if partner_id and partner_id.company_type == 'company':
                p_ids = partner_obj.search([('category_id.name', 'in',
                                             categ_list),
                                            ('parent_id', '!=', False),
                                            ('type', '=', p_type),
                                            ('parent_id', '=', partner_id.id)])
            if not partner_id:
                # If partner is not company gives all records
                p_ids = partner_obj.search([('category_id.name', 'in',
                                             categ_list),
                                            ('parent_id', '!=', False),
                                            ('type', '=', p_type)])
            return p_ids

    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        Onchange of partner to set prices based on valid contract of
        suppliers
        ---------------------------------
        @param self : object pointer
        """
        res = {'domain': {}}
        guide_contract_ids = []
        product_obj = self.env['product.product']
        for rec in self:
            if rec.partner_id:
                if self._context.get('params')\
                        or self._context.get(
                        'default_line_type') == 'transportation':
                    if self.product_id:
                        contract_ids = self.get_contract('transportation',
                                                         self.partner_id.id,
                                                         rec.
                                                         transport_order_id.
                                                         arrival_date,
                                                         rec.
                                                         transport_order_id.
                                                         return_date)
                        if contract_ids:
                            for contract_id in contract_ids:
                                for rate_id in contract_id.vehicle_rate_ids:
                                    if rate_id.vehicle_id.id == rec.\
                                            product_id.id:
                                        rec.from_time = rate_id.duration_from
                                        rec.price_unit = rate_id.rate
                if self._context.get('default_line_type') == 'tickets' or \
                   self._context.get('params'):
                    ticket_contract_id = self.get_contract('ticket', rec.
                                                           partner_id.id,
                                                           rec.
                                                           ticket_order_id.
                                                           arrival_date,
                                                           rec.
                                                           ticket_order_id.
                                                           return_date)
                    if ticket_contract_id:
                        for contract_rec in ticket_contract_id.\
                                ticket_contract_ids:
                            if rec.product_id.id == contract_rec.product_id.id:
                                rec.days_valid_ids = contract_rec.\
                                    days_valid_ids
                                rec.price_unit = contract_rec.price_unit
                if self._context.get('default_line_type') == 'tours' or \
                   self._context.get('params'):
                    tour_contract_id = self.get_contract('tour', rec.
                                                         partner_id.id,
                                                         rec.tour_order_id
                                                         .arrival_date,
                                                         rec.tour_order_id.
                                                         return_date)
                    if tour_contract_id:
                        for contract_rec in tour_contract_id.tour_contract_ids:
                            if rec.product_id.id == contract_rec.product_id.id:
                                rec.days_valid_ids = contract_rec.\
                                    days_valid_ids
                                rec.price_unit = contract_rec.price_unit
                if self._context.get('params') or \
                   self._context.get('default_line_type') == 'meal':
                    meal_contract_id = self.get_contract('meal', rec.
                                                         partner_id.id,
                                                         rec.meal_order_id.
                                                         arrival_date,
                                                         rec.meal_order_id.
                                                         return_date)
                    if meal_contract_id:
                        for contract_rec in meal_contract_id.\
                                meal_contract_ids1:
                            if rec.product_id.id == contract_rec.product_id.id:
                                rec.days_valid_ids = contract_rec.\
                                    days_valid_ids
                                rec.price_unit = contract_rec.price_unit
                                rec.restaurant_id = contract_rec.\
                                    restaurant_id.id
                                rec.menu_type_ids = contract_rec.menu_type_ids
            if self._context.get('params')\
                    or self._context.get('default_line_type') == 'visa':
                if self.product_id and self.partner_id:
                    contract_ids = self.get_contract('visa',
                                                     self.partner_id.id,
                                                     rec.visa_order_id.
                                                     arrival_date,
                                                     rec.visa_order_id.
                                                     return_date)
                    if contract_ids:
                        for contract_id in contract_ids:
                            for visa_rate_id in contract_id.visa_contract_ids:
                                if visa_rate_id.product_id.id == rec.\
                                        product_id.id:
                                    rec.price_unit = visa_rate_id.price_unit
            if self._context.get('default_line_type') == 'guide' or \
               self._context.get('params'):
                p_ids = self.get_contacts(rec.partner_id, 'contact', ['Guide',
                                                                      'guide'])
                if p_ids:
                    res['domain'].update({'guide_contact_id': [('id', 'in',
                                                                p_ids.ids)]})
                else:
                    res['domain'].update({'guide_contact_id': [('id', 'in',
                                                                [])]})
                guide_contract_ids = self.get_contract('guide', rec.
                                                       partner_id.id,
                                                       rec.sale_order_id.
                                                       arrival_date,
                                                       rec.sale_order_id.
                                                       return_date)
                if guide_contract_ids:
                    for contract_rec in guide_contract_ids:
                        for guide_rec in contract_rec.guide_contract_ids:
                            if guide_rec.product_id.id == rec.product_id.id:
                                self.price_unit = guide_rec.price_unit
                if self._context.get('default_line_type') == 'transaportation':
                    if not self.partner_id:
                        pro_ids = product_obj.search(
                            ['|',
                             ('categ_id.name',
                              '=', 'Transportation'),
                             ('categ_id.parent_id.name',
                              '=', 'Transportation')])
                        res['domain'].update({'product_id': [('id', 'in',
                                                              pro_ids.ids)]})
        return res

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        """
        Based on sellers defined in product suppliers populated for
        relevant product
        ---------------------------------
        @param self : object pointer
        """
        partner_obj = self.env['res.partner']
        product_obj = self.env['product.product']
        res = super(SaleOrderLine, self).product_id_change()
        for rec in self:
            if self._context.get('default_line_type') != 'transaportation'\
                    and self._context.get('field_parent') != 'transport_\
                                                                order_id':
                if self.product_id:
                    self.partner_id = False
                    self.price_unit = 0.0
                    self.days_valid_ids = False
                    self.ticket_day = False
                    self.menu_type_ids = False
                    self.guide_contact_id = False
            if not self._context.get('field_parent') == 'transport_order_id'\
                or not self._context.get(
                    'default_line_type') == 'transaportation':
                if self.product_id:
                    sellers = [x.name.id for x in rec.product_id.seller_ids]
                    if res:
                        res['domain'].update({'partner_id': [('id', 'in',
                                                              sellers)]})
            else:
                res['domain'].update({'partner_id': [('id', 'in', [])]})
            if not rec.product_id:
                rec.name = False
                supp_ids = self.env['res.partner'].search([('supplier', '=',
                                                            True)])
                res['domain'].update({'partner_id': [('id', 'in',
                                                      supp_ids.ids)]})
            if self._context.get('field_parent') == 'transport_order_id'\
                or self._context.get(
                    'default_line_type') == 'transaportation':
                if not self.partner_id:
                    product_domain = ['|',
                                      ('categ_id.name', '=', 'Transportation'),
                                      ('categ_id.parent_id.name',
                                       '=', 'Transportation')]
                    pro_ids = product_obj.search(product_domain)
                    res['domain'].update({'product_id': [('id', 'in',
                                                          pro_ids.ids)]})
                if self.partner_id:
                    contract_ids = self.get_contract('transportation',
                                                     self.partner_id.id,
                                                     rec.transport_order_id.
                                                     arrival_date,
                                                     rec.transport_order_id.
                                                     return_date)
                    if contract_ids:
                        for contract_id in contract_ids:
                            for rate_id in contract_id.vehicle_rate_ids:
                                if rate_id.vehicle_id.id == rec.product_id.id:
                                    rec.from_time = rate_id.duration_from
                                    rec.price_unit = rate_id.rate
            if self.product_id:
                sellers = [x.name.id for x in rec.product_id.seller_ids]
                if sellers:
                    res['domain'].update({'partner_id': [('id', 'in',
                                                          sellers)]})
                else:
                    supp_ids = partner_obj.search([('supplier', '=', True)])
                    res['domain'].update({'partner_id': [('id', 'in',
                                                          supp_ids.ids)]})
        return res

    @api.model
    def create(self, vals):
        if not vals.get('product_id'):
            vals.update({'product_uom': 1})
        if vals.get('product_id'):
            p_id = self.env['product.product'].browse(vals.get('product_id'))
            vals.update({'product_uom': p_id.uom_id.id})
        if vals.get('transport_order_id'):
            vals.update({'line_type': 'vehicle'})
        if vals.get('ticket_order_id'):
            vals.update({'line_type': 'tickets'})
        if vals.get('tour_order_id'):
            vals.update({'line_type': 'tours'})
        if vals.get('meal_order_id'):
            vals.update({'line_type': 'meal'})
        if vals.get('sale_order_id'):
            vals.update({'line_type': 'guide'})
        if vals.get('ticketing_order_id'):
            vals.update({'line_type': 'ticketing'})
        if vals.get('visa_order_id'):
            vals.update({'line_type': 'visa'})
        vals.update({'product_uom_qty': 1})
        res = super(SaleOrderLine, self).create(vals)
        res.tax_id = [(6, 0, [])]
        return res

    @api.depends('qty_invoiced', 'qty_delivered', 'product_uom_qty',
                                                  'order_id.state')
    def _get_to_invoice_qty(self):
        """
        Compute the quantity to invoice. If the invoice policy is order,
        the quantity to invoice is
        calculated from the ordered quantity. Otherwise,
        the quantity delivered is used.
        ---------------------------------
        @param self : object pointer
        """
        for line in self:
            if line.order_id.state in ['sale', 'done']:
                if line.product_id.invoice_policy == 'order':
                    line.qty_to_invoice = 1
                else:
                    line.qty_to_invoice = 1
            else:
                line.qty_to_invoice = 1

    qty_to_invoice = fields.Float(
        compute='_get_to_invoice_qty', string='To Invoice', store=True,
                readonly=True,
                digits=dp.get_precision('Product Unit of Measure'))

    name = fields.Text(string='Description', required=False)
    line_type = fields.Selection([('meal', 'Meal'), ('sale_line', 'Sale Line'),
                                  ('guide', 'Guide'),
                                  ('ticketing', 'Ticketing'),
                                  ('transaportation', 'Transaportation'),
                                  ('vehicle', 'Vehicle'),
                                  ('tickets', 'Tickets'), ('visa', 'Visa'),
                                  ('tours', 'Tours')], readonly=True,
                                 index=True,
                                 default=lambda self: self._context.get(
        'line_type', 'sale_line'),
        change_default=True,
        track_visibility='always')
    product_id = fields.Many2one('product.product', string='Product',
                                 domain=[('sale_ok', '=', True)],
                                 change_default=True,
                                 ondelete='restrict', required=False)
    partner_id = fields.Many2one('res.partner', 'Supplier')

    transport_order_id = fields.Many2one('sale.order', ondelete='cascade',
                                         string="Transportation", index=True,
                                         copy=False)
    transportation_date = fields.Datetime('Transportation Date')
    transportation_day = fields.Many2one('date.days', 'Transportation Days')
    days_id = fields.Many2one('date.days', 'Day')
    from_time = fields.Char('From Hours')
    to_time = fields.Float('To Hours')
    tag_ids = fields.Many2many(
        'product.attribute.value', string='Vehicle', ondelete='restrict')
    vehicle_type_id = fields.Many2one('vehicle.details', 'Vehicle Type')
    days = fields.Char("Days")
    ticket_order_id = fields.Many2one('sale.order', ondelete='cascade',
                                      string="Ticket", index=True, copy=False)
    tour_order_id = fields.Many2one('sale.order', ondelete='cascade',
                                    string="Tour", index=True,
                                    copy=False)
    start_time = fields.Float('From')
    end_time = fields.Float('To')
    ticket_date = fields.Datetime('Ticket Date')
    ticket_day = fields.Many2one('date.days', 'Ticket Day')
    week_days = fields.Selection([('0', 'Sunday'), ('1', 'Monday'),
                                  ('2', 'Tuesday'), ('3', 'Wednesday'),
                                  ('4', 'Thursday'), ('5', 'Friday'),
                                  ('6', 'Saturday')], default='0')
    meal_order_id = fields.Many2one('sale.order', ondelete='cascade',
                                    string='meal', index=True, copy=False)
    restaurant_id = fields.Many2one('res.partner', string="Restaurant")
    menu_type_ids = fields.Many2many('meal.menu', string="Menu Type")
    days_valid_ids = fields.Many2many('days.valid', string='Days Valid')
    guide_contact_id = fields.Many2one('res.partner')
    guide_lang = fields.Many2many('res.lang', 'sale_lang_rel', 'lang_id',
                                  'sale_id', 'Languages')
    ticketing_order_id = fields.Many2one('sale.order', ondelete='cascade',
                                         stirng="Ticketing", index=True,
                                         copy=False, required=False)
    route_start_id = fields.Many2one('airport', 'Source')
    route_end_id = fields.Many2one('airport', 'Destination')
    airline_id = fields.Many2one('tour.airline', "Airline")
    ticket_no = fields.Char("Ticket No.")
    meals = fields.Char('Meals')
    ticket_type = fields.Selection([('domestic', 'Domestic'),
                                    ('international', 'International')])
    ticket_issue_date = fields.Date('Issue Date')
    gross_fare = fields.Float('Gross Fare')
    passanger_id = fields.Many2one('res.partner', 'Passenger')

    order_id = fields.Many2one('sale.order', string='Order Reference',
                               required=False, ondelete='cascade',
                               index=True, copy=False)
    sale_order_id = fields.Many2one('sale.order', ondelete='cascade',
                                    string="Guide", index=True, copy=False)
    visa_order_id = fields.Many2one('sale.order', ondelete='cascade',
                                    stirng="Visa", index=True, copy=False)
    visa_status_id = fields.Many2one('visa.status', 'Visa Status')
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  required=False)
    day_date = fields.Date('Date')
    time = fields.Char("Time")

    @api.model
    def fields_view_get(self, view_id=None, view_type='form',
                        toolbar=False, submenu=False):
        result = super(SaleOrderLine, self).fields_view_get(
            view_id=view_id,
            view_type=view_type,
            toolbar=toolbar,
            submenu=submenu)
        if self._context.get('default_line_type'):

            doc = etree.fromstring(result['arch'])
            doc.set('create', 'false')
            doc.set('edit', 'false')
            result['arch'] = etree.tostring(doc)
        return result


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def _get_so(self):
        '''
        to find count of related sale order.
        ---------------------------------
        @param self : object pointer
        '''
        for rec in self:
            rec.so_count = len(rec.so_ids)

    @api.multi
    def action_view_quotation(self):
        sale_ids = self.mapped('so_ids')
        action = self.env.ref('sale.action_quotations').read()[0]
        if len(sale_ids) > 1:
            action['domain'] = [('id', 'in', sale_ids.ids)]
        elif len(sale_ids) == 1:
            action['views'] = [(self.env.ref('sale.view_order_form').id,
                                'form')]
            action['res_id'] = sale_ids.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def _default_pricelist(self):
        return self.env['product.pricelist'].search([('currency_id', '=',
                                                      self.env.user.company_id.
                                                      currency_id.id)],
                                                    limit=1)

    so_ids = fields.One2many('sale.order', 'package_id', string="Sale Orders")
    so_count = fields.Integer(string='# of Invoices', compute='_get_so',
                              readonly=True)
    group_cost_ids = fields.One2many('group.cost',
                                     'sale_order_id',
                                     'Group Cost',
                                     copy=True)
    currency_id = fields.Many2one("res.currency",
                                  related='pricelist_id.currency_id',
                                  string="Currency", readonly=True,
                                  required=False)
    pricelist_id = fields.Many2one('product.pricelist',
                                   string='Pricelist', required=False,
                                   readonly=True, states={'draft': [(
                                       'readonly',
                                       False)],
                                       'sent': [(
                                           'readonly',
                                           False)]},
                                   help="Pricelist for current sales order.",
                                   default=_default_pricelist)
    partner_invoice_id = fields.Many2one('res.partner',
                                         string='Invoice Address',
                                         readonly=True, required=False,
                                         states={'draft': [('readonly',
                                                            False)],
                                                 'sent': [('readonly',
                                                           False)]},
                                         help="Invoice address for current \
                                                 sales order.")
    partner_shipping_id = fields.Many2one('res.partner',
                                          string='Delivery Address',
                                          readonly=True,
                                          required=False, states={'draft': [(
                                              'readonly',
                                              False)],
                                              'sent': [(
                                                  'readonly',
                                                  False)]},
                                          help="Delivery address for current \
                                                  sales order.")
    partner_id = fields.Many2one('res.partner', string='Customer',
                                 readonly=True,
                                 states={'draft': [('readonly', False)],
                                         'sent': [('readonly', False)]},
                                 required=False,
                                 change_default=True, index=True,
                                 track_visibility='always')
    is_package = fields.Boolean('Is Package')
    website_published = fields.Boolean('Visible in Website', copy=False)
    website_url = fields.Char('Website URL', compute='_compute_website_url',
                              help='The full URL to access the document \
                              through the website.')
    profit_price = fields.Selection([
        ('fixed', 'Fix Price'),
        ('percentage', 'Percentage (discount)')], index=True, default='fixed')
    fixed_price = fields.Float('Fixed Price')
    percent_price = fields.Float('Percentage Price')
    package_id = fields.Many2one("sale.order", 'Sale Order')
    include_price = fields.Boolean("Include Visa Price", default=True,
                                   copy=False)
    include_ticket_price = fields.Boolean("Include Ticket Price", default=True,
                                          copy=False)
    show_details = fields.Boolean("Show more details", copy=True)

    @api.multi
    def write(self, values):
        passenger_obj = self.env['passenger.list']
        res = super(SaleOrder, self).write(values)
        p_ids = []
        for rec in self:
            if values.get('hotel_ids'):
                nw_count = 0
                for hotel_rec in rec.hotel_ids:
                    for rm_qty in range(hotel_rec.room_qty):
                        nw_count += 1
                        for np in range(hotel_rec.no_of_person):
                            if hotel_rec.room_accupacy_id and\
                                    hotel_rec.room_accupacy_id.room_selection\
                                    or False:
                                passenger_vals = {
                                    'number': str(nw_count) + '.' +
                                    str(rm_qty + 1) + '.' +
                                    str(np + 1),
                                    'room': hotel_rec.room_accupacy_id.
                                    room_selection.upper() or False,
                                    'hotel_id': hotel_rec.id
                                }
                                p_ids.extend(passenger_obj.create(
                                    passenger_vals).
                                    ids)
                rec.passenger_ids = [(6, 0, p_ids)]
        return res

    @api.onchange('profit_price')
    def onchange_profit_price(self):
        if self.profit_price == 'fixed':
            self.percent_price = 0.0
        elif self.profit_price == 'percentage':
            self.fixed_price = 0.0

    @api.constrains('profit_price')
    def check_profit_price(self):
        for rec in self:
            if self.profit_price == 'percentage':
                if self.percent_price > 100.0:
                    raise UserError(
                        _('Percentage can not be Greater than 100'))

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        """
        Create the invoice associated to the SO.
        :param grouped: if True, invoices are grouped by SO id. If False,
                        invoices are grouped by
                        (partner_invoice_id, currency)
        :param final: if True, refunds will be generated if necessary
        :returns: list of created invoices
        """
        inv_obj = self.env['account.invoice']
        precision = self.env['decimal.precision'].precision_get('Product Unit\
                                                                of Measure')
        invoices = {}
        references = {}
        for order in self:
            group_key = order.id if grouped else (order.partner_invoice_id.id,
                                                  order.currency_id.id)
            for line in order.order_line.sorted(key=lambda l: l.
                                                qty_to_invoice < 0):
                if float_is_zero(line.qty_to_invoice,
                                 precision_digits=precision):
                    continue
                if group_key not in invoices:
                    inv_data = order._prepare_invoice()
                    inv_data.update({'so_order_id': self.id})
                    invoice = inv_obj.create(inv_data)
                    references[invoice] = order
                    invoices[group_key] = invoice
                elif group_key in invoices:
                    vals = {}
                    if order.name not in invoices[group_key].origin.\
                       split(', '):
                        vals['origin'] = invoices[group_key].origin + ', '
                        + order.name
                    if order.client_order_ref and order.client_order_ref\
                            not in invoices[group_key].name.split(', ') and\
                            order.client_order_ref != invoices[group_key].name:
                        vals['name'] = invoices[group_key].name + ', '
                        + order.client_order_ref
                    invoices[group_key].write(vals)
                # No need to create invoice lines for package description
#                if line.qty_to_invoice > 0:
#                    line.invoice_line_create(invoices[group_key].id,
#                    line.qty_to_invoice)
#                elif line.qty_to_invoice < 0 and final:
#                    line.invoice_line_create(invoices[group_key].id,
#                    line.qty_to_invoice)
            new_val = {0: 'per_person', 1: 'sgl_supp', 2: 'per_person_tpl',
                       3: 'cwnb'}
            label_dict = {0: 'Per Person in DBL', 1: 'SGL Supp',
                          2: 'Per Person in TPL', 3: 'CWNB'}
            for i in range(4):
                journal_id = self.env['account.invoice']._default_journal()
                account = journal_id.default_credit_account_id
                inv_line_res = {
                    'name': label_dict[i],
                    'origin': self.name,
                    'account_id': account.id,
                    'price_unit': self.read([new_val[i]])[0].get(new_val[i]),
                    'quantity': 1,
#                    'account_analytic_id': self.project_id.id,
                    'invoice_id': invoices[group_key].id,
                }
                self.env['account.invoice.line'].create(inv_line_res)
            if references.get(invoices.get(group_key)):
                if order not in references[invoices[group_key]]:
                    references[invoice] = references[invoice] | order
        if not invoices:
            raise UserError(_('There is no invoiceable line.'))

        for invoice in invoices.values():
            if not invoice.invoice_line_ids:
                raise UserError(_('There is no invoiceable line.'))
            # If invoice is negative, do a refund invoice instead
            if invoice.amount_untaxed < 0:
                invoice.type = 'out_refund'
                for line in invoice.invoice_line_ids:
                    line.quantity = -line.quantity
            # Use additional field helper function (for account extensions)
            for line in invoice.invoice_line_ids:
                line._set_additional_fields(invoice)
            # Necessary to force computation of taxes. In account_invoice,
            # they are triggered
            # by onchanges, which are not triggered when doing a create.
            invoice.compute_taxes()
            invoice.message_post_with_view('mail.message_origin_link',
                                           values={'self': invoice,
                                                   'origin': references[
                                                       invoice]},
                                           subtype_id=self.env.ref(
                                               'mail.mt_note').id)
        return [inv.id for inv in invoices.values()]

    @api.model
    def create(self, vals):
        arrival_date = return_date = False
        passenger_obj = self.env['passenger.list']
        """
        override create method for skip sequence number when creating record
        for package.
        and also for creation of itinerary based on arrival and departure date
        """
        product = self.env.ref(
            'tour_travel_package_design.t_product_product_demo')
        if self._context.get('display_package'):
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = ('Package')
            #  Makes sure partner_invoice_id', 'partner_shipping_id' and
            #  'pricelist_id' are defined
            if any(f not in vals for f in ['partner_invoice_id',
                                           'partner_shipping_id',
                                           'pricelist_id']):
                partner = self.env['res.partner'].browse(vals.
                                                         get('partner_id'))
                addr = partner.address_get(['delivery', 'invoice'])
                vals['partner_invoice_id'] = vals.setdefault(
                    'partner_invoice_id', addr['invoice'])
                vals['partner_shipping_id'] = vals.setdefault(
                    'partner_shipping_id', addr['delivery'])
                vals['pricelist_id'] = vals.setdefault(
                    'pricelist_id',
                    partner.property_product_pricelist and
                    partner.
                    property_product_pricelist.id)
            result = super(SaleOrder, self).create(vals)
            if not result.passenger_ids:
                nw_count = 0
                for hotel_rec in result.hotel_ids:
                    existing_passenger_ids = passenger_obj.search([(
                        'hotel_id',
                        '=',
                        hotel_rec.id)])
                    if existing_passenger_ids:
                        existing_passenger_ids.unlink()
                    for rm_qty in range(hotel_rec.room_qty):
                        nw_count += 1
                        for np in range(hotel_rec.no_of_person):
                            passenger_vals = [(0, 0, {
                                'number': str(nw_count) + '.' +
                                str(rm_qty + 1) + '.' + str(np + 1),
                                'room': hotel_rec.room_accupacy_id.
                                room_selection.upper() or False,
                                'so_id': self.id,
                                'hotel_id': hotel_rec.id
                            })]
                            result.passenger_ids = passenger_vals
            if not result.order_line:
                if result.arrival_date:
                    arrival_date = result.arrival_date
                if result.return_date:
                    return_date = result.return_date
                if arrival_date and return_date:
                    arrival_date_str = arrival_date.strftime('%Y-%m-%d')
                    start_date = datetime.strptime(arrival_date_str,
                                                   DEFAULT_SERVER_DATE_FORMAT)
                    return_date_str = return_date.strftime('%Y-%m-%d')
                    end_date = datetime.strptime(return_date_str,
                                                 DEFAULT_SERVER_DATE_FORMAT)
                    days = (end_date - start_date).days + 1
                    sale_line = []

                    for i in range(days):
                        start_date_str = start_date.date()
                        day_vals = {
                            'name': 'Day ' + str(i + 1),
                                    'sale_day_id': result.id,
                                    'hotel_date': start_date +
                            relativedelta(days=i)
                        }
                        self.env['date.days'].create(day_vals)

                        vals = (0, 0, {'days': 'Day ' + str(i + 1),
                                       'day_date': start_date_str +
                                       relativedelta(days=i),
                                       'name': 'Day ' + str(i + 1),
                                       'order_id': result.id,
                                       'product_id': product.id})

                        sale_line.append(vals)
                    result.order_line = sale_line
            return result
        else:
            if vals.get('name', _('New')) == _('New'):
                if 'company_id' in vals:
                    vals['name'] = self.env['ir.sequence'].with_context(
                        force_company=vals['company_id']).next_by_code(
                        'sale.order') or _('New')
                else:
                    vals['name'] = self.env['ir.sequence'].next_by_code(
                        'sale.order') or _('New')
            #  Makes sure partner_invoice_id', 'partner_shipping_id'
#             and 'pricelist_id' are defined
            if any(f not in vals for f in ['partner_invoice_id',
                                           'partner_shipping_id',
                                           'pricelist_id']):
                partner = self.env['res.partner'].browse(
                    vals.get('partner_id'))
                addr = partner.address_get(['delivery', 'invoice'])
                vals['partner_invoice_id'] = vals.setdefault(
                    'partner_invoice_id', addr['invoice'])
                vals['partner_shipping_id'] = vals.setdefault(
                    'partner_shipping_id', addr['delivery'])
                vals['pricelist_id'] = vals.setdefault(
                    'pricelist_id',
                    partner.property_product_pricelist and
                    partner.property_product_pricelist.id)
            result = super(SaleOrder, self).create(vals)
            if not result.passenger_ids:
                nw_count = 0
                for hotel_rec in result.hotel_ids:
                    existing_passenger_ids = passenger_obj.search(
                        [('hotel_id', '=', hotel_rec.id)])
                    if existing_passenger_ids:
                        existing_passenger_ids.unlink()
                    for rm_qty in range(hotel_rec.room_qty):
                        nw_count += 1
                        for np in range(hotel_rec.no_of_person):
                            passenger_vals = [(0, 0, {
                                'number': str(nw_count) + '.' + str(
                                    rm_qty + 1) + '.' + str(np + 1),
                                'room': hotel_rec.room_accupacy_id.
                                room_selection.upper() or False,
                                'so_id': self.id,
                                'hotel_id': hotel_rec.id
                            })]
                            result.passenger_ids = passenger_vals
            if not result.order_line:
                if result.arrival_date:
                    arrival_date = result.arrival_date
                if result.return_date:
                    return_date = result.return_date
                if arrival_date and return_date:
                    arrival_date_str = arrival_date.strftime('%Y-%m-%d')
                    return_date_str = return_date.strftime('%Y-%m-%d')
                    start_date = datetime.strptime(arrival_date_str,
                                                   DEFAULT_SERVER_DATE_FORMAT)
                    end_date = datetime.strptime(arrival_date_str,
                                                 DEFAULT_SERVER_DATE_FORMAT)
                    days = (end_date - start_date).days + 1
                    sale_line = []
                    result.order_line = []

                    for i in range(days):
                        start_date_date = start_date.date()
                        day_vals = {
                            'name': 'Day ' + str(i + 1),
                                    'sale_day_id': result.id,
                                    'hotel_date': start_date +
                            relativedelta(days=i)
                        }
                        self.env['date.days'].create(day_vals)
                        vals = (0, 0, {'days': 'Day ' + str(i + 1),
                                       'day_date': start_date_date +
                                       relativedelta(days=i),
                                       'name': 'Day ' + str(i + 1),
                                       'order_id': result.id,
                                       'product_id': product.id
                                       })
                        sale_line.append(vals)
                    result.order_line = sale_line
        return result

    @api.multi
    def _compute_website_url(self):
        for record in self:
            record.website_url = '#'

    @api.multi
    def website_publish_button(self):
        self.ensure_one()
        if self.env.user.has_group('website.group_website_publisher') \
                and self.website_url != '#':
            return self.open_website_url()
        return self.write({'website_published': not self.website_published})

    def open_website_url(self):
        return {
            'type': 'ir.actions.act_url',
            'url': self.website_url,
            'target': 'self',
        }

    @api.multi
    def create_days(self, arrival_date, return_date, sale_id):
        """
        Method using for creation of days based on arrival date and
        return date
        """
        day_obj = self.env['date.days']
        for rec in self:
            if arrival_date or return_date:
                arrival_date_str = arrival_date.strftime('%Y-%m-%d')
                return_date_str = return_date.strftime('%Y-%m-%d')
                start_date = datetime.strptime(arrival_date_str,
                                               DEFAULT_SERVER_DATE_FORMAT)
                end_date = datetime.strptime(return_date_str,
                                             DEFAULT_SERVER_DATE_FORMAT)
                days = (end_date - start_date).days + 1
                days_ids = day_obj.search([('sale_day_id', '=', sale_id.id)])
                if days_ids:
                    self._cr.execute("delete from date_days where id in %s", (
                        tuple(days_ids.ids),))
                for i in range(days):
                    day_vals = {'name': 'Day ' + str(i + 1),
                                'hotel_date': start_date + relativedelta(
                                    days=i),
                                'sale_day_id': sale_id.id,
                                }
                    day_obj.create(day_vals)
        return True

    @api.multi
    def copy(self, default=None):
        """
        override copy method for execute onchange for dates
        """
        res = super(SaleOrder, self).copy(default)
        if res.arrival_date or res.return_date:
            self.create_days(res.arrival_date, res.return_date, res)
            if res.transaportation_ids:
                for t_rec in res.transaportation_ids:
                    if t_rec.transportation_day:
                        copy_day_id = self.env['date.days'].search(
                            [('name', '=', t_rec.transportation_day.name),
                                ('sale_day_id', '=', res.id)], limit=1)
                        t_rec.transportation_day = copy_day_id.id
            if res.hotel_ids:
                for hotel_rec in res.hotel_ids:
                    if hotel_rec.from_date:
                        copy_day_id = self.env['date.days'].search(
                            [('name', '=', hotel_rec.from_date.name),
                             ('sale_day_id', '=', res.id)], limit=1)
                        hotel_rec.from_date = copy_day_id.id
                    if hotel_rec.to_date:
                        copy_day_id = self.env['date.days'].search(
                            [('name', '=', hotel_rec.to_date.name),
                             ('sale_day_id', '=', res.id)], limit=1)
                        hotel_rec.to_date = copy_day_id.id
            if res.ticket_ids:
                for ticket_rec in res.ticket_ids:
                    if ticket_rec.ticket_day:
                        copy_day_id = self.env['date.days'].search(
                            [('name', '=', ticket_rec.ticket_day.name),
                             ('sale_day_id', '=', res.id)], limit=1)
                        ticket_rec.ticket_day = copy_day_id.id
            if res.tour_ids:
                for tour_rec in res.tour_ids:
                    if tour_rec.ticket_day:
                        copy_day_id = self.env['date.days'].search(
                            [('name', '=', tour_rec.ticket_day.name),
                             ('sale_day_id', '=', res.id)], limit=1)
                        tour_rec.ticket_day = copy_day_id.id
            if res.meal_ids:
                for meal_rec in res.meal_ids:
                    if meal_rec.days_id:
                        copy_day_id = self.env['date.days'].search(
                            [('name', '=', meal_rec.days_id.name),
                             ('sale_day_id', '=', res.id)], limit=1)
                        meal_rec.days_id = copy_day_id.id
            if res.guide_ids:
                for guide_rec in res.guide_ids:
                    if guide_rec.days_id:
                        copy_day_id = self.env['date.days'].search(
                            [('name', '=', guide_rec.days_id.name),
                             ('sale_day_id', '=', res.id)], limit=1)
                        guide_rec.days_id = copy_day_id.id
        return res

    @api.multi
    def copy_quotation(self):
        for rec in self:
            """
            override copy method for creation of Quotation from package
            """
            res = super(SaleOrder, self).with_context({'hide_sale': True,
                                                       'display_package':
                                                       False}).copy({})
            res.update({'is_package': False, 'package_id': rec.id})
            context = dict(self._context or {})
            context['hide_sale'] = True
            try:
                form_id = self.env.ref('sale.view_order_form').id
            except ValueError:
                form_id = False
            return {
                'name': _('Quotation'),
                'view_mode': 'form',
                'view_id': form_id,
                'res_model': 'sale.order',
                'context': context,
                'type': 'ir.actions.act_window',
                'domain': [('is_package', '=', False), ('id', 'in', [res.id])],
                'res_id': res.id,
            }

    @api.depends('order_line.price_total',
                 'guide_ids.price_total',
                 'ticket_ids.price_total',
                 'tour_ids.price_total',
                 'meal_ids.price_total',
                 'transaportation_ids.price_total',
                 'ticketing_ids.price_total',
                 'visa_ids.price_total',
                 'hotel_ids.price_unit', 'hotel_ids.product_uom_qty'
                 )
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_tax = 0.0
            amount_untaxed = 0.0
            transport = 0.0
            for hotel_line in order.hotel_ids:
                amount_untaxed += hotel_line.price_subtotal
            for tour_line in order.tour_ids:
                amount_untaxed += tour_line.price_subtotal
            for ticketing_line in order.ticketing_ids:
                amount_untaxed += ticketing_line.price_subtotal
            for transport_line in order.transaportation_ids:
                transport += transport_line.price_subtotal
                amount_untaxed += transport_line.price_subtotal
            for meal_line in order.meal_ids:
                amount_untaxed += meal_line.price_subtotal
            for ticket_line in order.ticket_ids:
                amount_untaxed += ticket_line.price_subtotal
            for guide_line in order.guide_ids:
                amount_untaxed += guide_line.price_subtotal
            for visa_line in order.visa_ids:
                amount_untaxed += visa_line.price_subtotal
            for ticketing in order.ticketing_ids:
                if order.company_id.tax_calculation_rounding_method == \
                        'round_globally':
                    price = ticketing.price_unit * (1 - (
                        ticketing.discount or 0.0) / 100.0)
                    taxes = ticketing.tax_id.compute_all(
                        price,
                        ticketing.order_id.currency_id,
                        ticketing.product_uom_qty,
                        product=ticketing.product_id,
                        partner=order.partner_shipping_id)
                    amount_tax += sum(t.get('amount', 0.0) for t in
                                      taxes.get('taxes', []))
                else:
                    amount_tax += ticketing.price_tax
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                #  FORWARDPORT UP TO 10.0
                if order.company_id.tax_calculation_rounding_method == \
                        'round_globally':
                    price = line.price_unit * (1 - (
                        line.discount or 0.0) / 100.0)
                    taxes = line.tax_id.compute_all(
                        price,
                        line.order_id.currency_id,
                        line.product_uom_qty,
                        product=line.product_id,
                        partner=order.partner_shipping_id)
                    amount_tax += sum(t.get('amount', 0.0) for t in
                                      taxes.get('taxes', []))
                else:
                    amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.pricelist_id.currency_id.round(
                    amount_untaxed),
                'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })

    @api.onchange('arrival_date', 'return_date')
    def onchange_arrival_return_date(self):
        product = self.env.ref(
            'tour_travel_package_design.t_product_product_demo')
        day_obj = self.env['date.days']
        arrival_date = return_date = False
        if self.order_line:
            # Create Itinery lines based on arrival and departure date of
            # package
            if self.arrival_date:
                arrival_date = self.arrival_date
            if self.return_date:
                return_date = self.return_date
            if arrival_date and return_date:
                arrival_date_str = arrival_date.strftime('%Y-%m-%d')

                return_date_str = return_date.strftime('%Y-%m-%d')
                start_date = datetime.strptime(arrival_date_str,
                                               DEFAULT_SERVER_DATE_FORMAT)
                end_date = datetime.strptime(return_date_str,
                                             DEFAULT_SERVER_DATE_FORMAT)
                # difference between two dates
                days = (end_date - start_date).days + 1
                if len(self.order_line.ids) > days:
                    # if arrival date changes
                    sale_line_ids1 = []
                    if self._context.get('change_arrival'):

                        min_date = len(self.order_line) - days
                        sale_line_ids = self.env['sale.order.line'].search(
                            [('order_id', '=', self._origin.id),
                             ('line_type', '=', 'sale_line')],
                            limit=min_date, order='id DESC')
                        for line in sale_line_ids:
                            self._cr.execute("update sale_order_line set \
                            order_id = null where id = %s and order_id = %s \
                            and line_type = %s", (line.id, self._origin.id,
                                                  'sale_line'))
                        day_line_ids = self.env['date.days'].search(
                            [('sale_day_id', '=', self._origin.id)],
                            limit=min_date, order='id DESC')
                        if day_line_ids:
                            for line_day in day_line_ids:
                                self._cr.execute("update date_days set \
                                sale_day_id = null where id = %s and \
                                sale_day_id = %s", (
                                    line_day.id, self._origin.id))
                        day_line_ids1 = self.env['date.days'].search(
                            [('sale_day_id', '=', self._origin.id)])
                        t_cnt = 0
                        for d_line in day_line_ids1:
                            final_date = start_date + relativedelta(days=t_cnt)
                            t_cnt += 1
                            self._cr.execute("update date_days set hotel_date \
                            = %s where sale_day_id = %s and id = %s",
                                             (str(final_date),
                                              self._origin.id, d_line.id))
                        sale_line_ids1 = self.env['sale.order.line'].search(
                            [('line_type', '=', 'sale_line'),
                             ('order_id', '=', self._origin.id)])
                        cnt = 0
                        start_date_str = start_date.date()
                        for i_line in sale_line_ids1:
                            i_line.days = 'Day' + str(cnt + 1)
                            i_line.name = 'Day' + str(cnt + 1)
                            # i_line.display_type = False
                            i_line.product_id = product.id
                            i_line.day_date = start_date_str + relativedelta(
                                days=cnt)
                            cnt += 1
                        self.order_line = [(6, 0, sale_line_ids1.ids)]
                    if self._context.get('change_return'):
                        max_lines = len(self.order_line) - days
                        sale_line_ids = self.env['sale.order.line'].search(
                            [('line_type', '=', 'sale_line'),
                             ('order_id', '=', self._origin.id)],
                            limit=max_lines, order='id DESC')
                        for line in sale_line_ids:
                            self._cr.execute("update sale_order_line set \
                            order_id = null  where id = %s and order_id = %s \
                            and line_type = %s", (line.id, self._origin.id,
                                                  'sale_line'))
                        sale_line_ids1 = self.env['sale.order.line'].search(
                            [('line_type', '=', 'sale_line'),
                             ('order_id', '=', self._origin.id)])
                        cnt = 0
                        start_date_str = start_date.date()
                        for i_line in sale_line_ids1:
                            i_line.days = 'Day' + str(cnt + 1)
                            i_line.name = 'Day' + str(cnt + 1)
                            # i_line.display_type = False
                            i_line.product_id = product.id
                            i_line.day_date = start_date_str + relativedelta(
                                days=cnt)
                            cnt += 1
                        self.order_line = [(6, 0, sale_line_ids1.ids)]
                        day_line_ids = self.env['date.days'].search(
                            [('sale_day_id', '=', self._origin.id)],
                            limit=max_lines, order='id DESC')
                        if day_line_ids:
                            for line_day in day_line_ids:
                                self._cr.execute("update date_days set \
                                sale_day_id = null where id = %s and \
                                sale_day_id = %s", (
                                    line_day.id, self._origin.id))
                                self._cr.execute("delete from date_days \
                                where id = %s and sale_day_id = %s", (
                                    line_day.id, self._origin.id))
                        day_line_ids1 = self.env['date.days'].search(
                            [('sale_day_id', '=', self._origin.id)])
                        t_cnt = 0
                        for d_line in day_line_ids1:
                            final_date = start_date + relativedelta(days=t_cnt)
                            t_cnt += 1
                            d_line.name = 'Day' + str(t_cnt)
                            d_line.product_id = product.id
                            self._cr.execute("update date_days set \
                            hotel_date = %s where sale_day_id = %s and \
                            id = %s", (str(final_date), self._origin.id,
                                       d_line.id))
                # for increasing lines
                if len(self.order_line.ids) < days:
                    if self._context.get('change_arrival'):
                        extra_days = days - len(self.order_line)
                        sale_line_ids1 = []
                        nw_so_line = []
                        for i in range(extra_days):
                            str_dt = start_date.date()
                            day_vals = {'name': 'Day ' + str(
                                len(self.order_line) + 1),
                                'hotel_date': str_dt + relativedelta(
                                    days=i),
                                'sale_day_id': self._origin.id,
                            }
                            day_obj.create(day_vals)
                            day_str = 'Day ' + str(len(self.order_line) + 1)
                            date_str = str_dt + relativedelta(
                                days=len(self.order_line))
                            so_line_vals = {
                                'days': day_str,
                                'day_date': date_str,
                                'product_id': product.id,
                                'line_type': 'sale_line',
                                'order_id': self._origin.id,
                                'price_unit': 0.0,
                                'product_uom_qty': 1,
                                'customer_lead': 1
                            }
                            store_so_lines = self.order_line.ids
                            so_line1 = self.env[
                                'sale.order.line'].create(so_line_vals)
                            nw_so_line = [so_line1.id]
                            so_lines = store_so_lines
                            # nw_so_line = self.order_line.ids
                            if nw_so_line:
                                so_lines.append(nw_so_line[0])
                            self.order_line = [(6, 0, so_lines)]
                            cnt = 0
                            for i_line in self.order_line:
                                start_dt1 = start_date.date()
                                i_line.days = 'Day' + str(cnt + 1)
                                i_line.name = 'Day' + str(cnt + 1)
                                i_line.product_id = product.id
                                i_line.day_date = start_dt1 + relativedelta(
                                    days=cnt)
                                cnt += 1
                            day_line_ids1 = self.env['date.days'].search(
                                [('sale_day_id', '=', self._origin.id)])
                            t_cnt = 0
                            for d_line in day_line_ids1:
                                str_dt = start_date.date()
                                final_date = str_dt + relativedelta(
                                    days=t_cnt)
                                t_cnt += 1
                                self._cr.execute("update date_days set \
                                hotel_date = %s where sale_day_id = %s and id \
                                = %s", (str(final_date),
                                        self._origin.id, d_line.id))
                    if self._context.get('change_return'):
                        so_line = []
                        extra_days = days - len(self.order_line)
                        for i in range(extra_days):
                            strt_dt = start_date.date()
                            day_vals = {'name': 'Day ' + str(
                                len(self.order_line) + 1),
                                'hotel_date': strt_dt + relativedelta(
                                days=len(self.order_line)),
                                'sale_day_id': self._origin.id,
                            }
                            day_obj.create(day_vals)
                            day_str = 'Day ' + str(len(self.order_line) + 1)
                            date_str = strt_dt + relativedelta(
                                days=len(self.order_line))

                            sol_vals = {
                                'days': day_str,
                                'day_date': date_str,
                                'product_id': product.id,
                                'line_type': 'sale_line',
                                'order_id': self._origin.id,
                                'price_unit': 0.0,
                                'product_uom_qty': 1,
                                'customer_lead': 1
                            }
                            store_sol = self.order_line.ids
                            sale_lines = self.env[
                                'sale.order.line'].create(sol_vals)
                            new_so_line = [sale_lines.id]
                            so_line = store_sol
                            if new_so_line:
                                so_line.append(new_so_line[0])
                            self.order_line = [(6, 0, so_line)]
                            cnt = 0
                            for i_line in self.order_line:
                                start_dt = start_date.date()
                                i_line.days = 'Day' + str(cnt + 1)
                                i_line.product_id = product.id
                                i_line.name = 'Day' + str(cnt + 1)
                                i_line.day_date = start_dt + relativedelta(
                                    days=cnt)
                                cnt += 1

            self._cr.execute("delete from date_days where sale_day_id is null")
        # vals = [(0, 0, {'days': 'Day ' + str(1),
        #                            # 'day_date': datetime.date.today(),
        #                            'name': 'Day ' + str(1),
        #                            'product_id': 4
        #                            })]
        # print("vals=========", vals)
        # self.order_line = vals

    @api.depends('order_line.price_total',
                 'guide_ids.price_unit',
                 'ticket_ids.price_unit',
                 'tour_ids.price_unit',
                 'meal_ids.price_unit',
                 'visa_ids.price_unit',
                 'include_price',
                 'transaportation_ids.price_unit',
                 'ticketing_ids.price_unit',
                 'include_ticket_price',
                 'hotel_ids.price_unit', 'fixed_price',
                 'percent_price')
    def _get_per_person(self):
        extra_bed = 0.0
        for order in self:
            hotel_ttl = 0.0
            single_price = double_price = tpl_price = 0.0
            for hotel_line in order.hotel_ids:
                if hotel_line.room_accupacy_id.room_selection == 'single':
                    if hotel_line.no_of_person != 0:
                        single_price += \
                            hotel_line.price_subtotal / hotel_line.room_qty
                if hotel_line.room_accupacy_id.room_selection == 'double':
                    if hotel_line.no_of_person != 0:
                        double_price += \
                            hotel_line.price_subtotal / hotel_line.no_of_person
                if hotel_line.room_accupacy_id.room_selection == 'tpl':
                    if hotel_line.no_of_person != 0:
                        tpl_price += \
                            hotel_line.price_subtotal / hotel_line.no_of_person
                hotel_ttl += hotel_line.price_subtotal
                extra_bed += \
                    hotel_line.extra_bed_price * hotel_line.product_uom_qty
            final_air_ticket_price = 0.0
            if order.include_ticket_price:
                for airticket_line in order.ticketing_ids:
                    final_air_ticket_price += airticket_line.price_unit
            final_visa_price = 0.0
            if order.include_price:
                for visa_line in order.visa_ids:
                    final_visa_price += visa_line.price_unit
            tours = 0.0
            final_tour_price = 0.0
            for tour_line in order.tour_ids:
                tours += tour_line.price_subtotal
                if order.pax_group != 0.0:
                    final_tour_price = tours / order.pax_group
            transport = 0.0
            final_price = 0.0
            for transport_line in order.transaportation_ids:
                transport += transport_line.price_subtotal
                if order.pax_group != 0.0:
                    final_price = transport / order.pax_group
            ticket = 0.0
            ticket_final_total = 0.0
            for ticket_line in order.ticket_ids:
                ticket += ticket_line.price_subtotal
                if order.pax_group != 0.0:
                    ticket_final_total = ticket / order.pax_group
            guide_total = 0.0
            final_guide_total = 0.0
            for guide_line in order.guide_ids:
                guide_total += guide_line.price_subtotal
                if order.pax_group != 0.0:
                    final_guide_total = guide_total / order.pax_group
            meal_total = 0.0
            final_meal_total = 0.0
            for meal_line in order.meal_ids:
                meal_total += meal_line.price_subtotal
                if order.pax_group != 0.0:
                    final_meal_total = meal_total / order.pax_group
            order.per_person = double_price + final_air_ticket_price + \
                final_tour_price + final_visa_price + final_price + \
                final_guide_total + ticket_final_total + final_meal_total
            order.sgl_supp = single_price + final_air_ticket_price + \
                final_tour_price + final_visa_price + final_price + \
                final_guide_total + ticket_final_total + final_meal_total
            order.per_person_tpl = tpl_price + final_air_ticket_price + \
                final_tour_price + final_meal_total + final_visa_price + \
                final_guide_total + ticket_final_total + final_price
            order.cwnb = final_meal_total + final_guide_total + \
                final_air_ticket_price + final_tour_price + \
                ticket_final_total + \
                final_price + final_visa_price

    @api.model
    def _get_currency(self):
        return self.env.user.company_id.currency_id

    @api.depends('usd_currency_id', 'per_person', 'sgl_supp',
                 'per_person_tpl', 'cwnb')
    def get_usd_cost(self):
        for order in self:
            today = datetime.today()
            usd_per_person = order.currency_id._convert(
                order.per_person, order.usd_currency_id,
                order.company_id, today)
            usd_sgl_supp = order.currency_id._convert(order.sgl_supp,
                                                      order.usd_currency_id,
                                                      order.company_id, today)
            usd_per_person_tpl = order.currency_id._convert(
                order.per_person_tpl, order.usd_currency_id,
                order.company_id, today)
            usd_cwnb = order.currency_id._convert(
                order.cwnb,
                order.usd_currency_id,
                order.company_id, today)
            # Calculation of profit amount fixed/percentage for per person
            if order.fixed_price and usd_per_person != 0.0:
                order.usd_per_person = usd_per_person + order.fixed_price
            elif order.percent_price and usd_per_person != 0.0:
                order.usd_per_person = usd_per_person + (
                    usd_per_person * order.percent_price / 100)
            else:
                order.usd_per_person = usd_per_person
            # Calculation of profit amount fixed/percentage for single person
            if order.fixed_price and usd_sgl_supp != 0.0:
                order.usd_sgl_supp = usd_sgl_supp + order.fixed_price
            elif order.percent_price and usd_sgl_supp != 0.0:
                order.usd_sgl_supp = usd_sgl_supp + (
                    usd_sgl_supp * order.percent_price / 100)
            else:
                order.usd_sgl_supp = usd_sgl_supp
            # Calculation of profit amount fixed/percentage for per person tpl
            if order.fixed_price and usd_per_person_tpl != 0.0:
                order.usd_per_person_tpl = usd_per_person_tpl + \
                    order.fixed_price
            elif order.percent_price and usd_per_person_tpl != 0.0:
                order.usd_per_person_tpl = usd_per_person_tpl + (
                    usd_per_person_tpl * order.percent_price / 100)
            else:
                order.usd_per_person_tpl = usd_per_person_tpl
            # Calculation of profit amount fixed/percentage for per person cwnb
            if order.fixed_price and usd_cwnb != 0.0:
                order.usd_cwnb = usd_cwnb + order.fixed_price
            elif order.percent_price and usd_cwnb != 0.0:
                order.usd_cwnb = usd_cwnb + (usd_cwnb *
                                             order.percent_price / 100)
            else:
                order.usd_cwnb = usd_cwnb
    per_person = fields.Monetary('Per person in DOUBLE',
                                 compute='_get_per_person')
    sgl_supp = fields.Monetary('Per person in SINGLE',
                               compute='_get_per_person')
    per_person_tpl = fields.Monetary('Per person in TRIPLE',
                                     compute='_get_per_person')
    cwnb = fields.Monetary('CWNB', compute='_get_per_person')
    usd_per_person = fields.Monetary(currency_field='usd_currency_id',
                                     string='Per person in DBL',
                                     compute='get_usd_cost'
                                     )
    usd_sgl_supp = fields.Monetary(currency_field='usd_currency_id',
                                   string='Per person in SGL',
                                   compute='get_usd_cost'
                                   )
    usd_per_person_tpl = fields.Monetary(currency_field='usd_currency_id',
                                         string='Per person in TPL',
                                         compute='get_usd_cost'
                                         )
    usd_cwnb = fields.Monetary(currency_field='usd_currency_id',
                               string='USD CWNB', compute='get_usd_cost'
                               )
    usd_currency_id = fields.Many2one('res.currency', string='USD Currency',
                                      default=_get_currency
                                      )
    travel_date = fields.Datetime('Travel Date', readonly=True,
                                  states={'draft': [('readonly', False)],
                                          'sent': [('readonly', False)]}
                                  )
    arrival_date = fields.Date('Arrival Date', readonly=True,
                               states={'draft': [('readonly', False)],
                                       'sent': [('readonly', False)]},
                               help="Expected date come to\
                                a hotel or other location"
                               )
    agent_id = fields.Many2one('res.partner', 'Agent', readonly=True,
                               states={'draft': [('readonly', False)],
                                       'sent': [('readonly', False)]},
                               help="Responsible for\
                 organize tours or for providing travel services"
                               )
    return_date = fields.Date('Departure Date', readonly=True,
                              states={'draft': [('readonly', False)],
                                      'sent': [('readonly', False)]}, help="Expected date to\
                   leave a hotel or other location."
                              )
    pax_group = fields.Integer('No of Participants', readonly=True,
                               states={'draft': [('readonly', False)],
                                       'sent': [('readonly', False)]}, help="Number of\
                         Persons participating in current package")
    guide_ids = fields.One2many('sale.order.line', 'sale_order_id',
                                string='Guides', states={'cancel': [
                                    ('readonly', True)],
                                    'done': [
                                    ('readonly', True)]},
                                copy=True
                                )
    ticket_ids = fields.One2many('sale.order.line', 'ticket_order_id',
                                 string='Tickets', states={'cancel': [
                                     ('readonly', True)],
                                     'done': [
                                     ('readonly', True)]},
                                 copy=True
                                 )
    tour_ids = fields.One2many('sale.order.line', 'tour_order_id',
                               string='Tours', states={'cancel': [
                                   ('readonly', True)],
                                   'done': [
                                   ('readonly', True)]},
                               copy=True
                               )
    meal_ids = fields.One2many('sale.order.line', 'meal_order_id',
                               string='Meal', states={'cancel': [
                                   ('readonly', True)],
                                   'done': [
                                   ('readonly', True)]},
                               copy=True
                               )
    transaportation_ids = fields.One2many('sale.order.line',
                                          'transport_order_id',
                                          string='Transport',
                                          states={'cancel': [
                                              ('readonly', True)],
                                              'done': [
                                                  ('readonly', True)]},
                                          copy=True
                                          )
    ticketing_ids = fields.One2many('sale.order.line', 'ticketing_order_id',
                                    string='Ticket', states={'cancel': [
                                        ('readonly', True)],
                                        'done': [
                                        ('readonly', True)]},
                                    copy=True
                                    )
    hotel_ids = fields.One2many('hotel.contract', 'sale_id',
                                string="Hotel", states={'cancel': [
                                    ('readonly', True)],
                                    'done': [
                                    ('readonly', True)]},
                                copy=True
                                )
    visa_ids = fields.One2many('sale.order.line', 'visa_order_id', "Visa",
                               states={'cancel': [('readonly', True)],
                                       'done': [('readonly', True)]}, copy=True
                               )
    passenger_ids = fields.One2many('passenger.list', 'so_id',
                                    string='Passenger', states={'cancel': [
                                        ('readonly', True)],
                                        'done': [
                                        ('readonly', True)]},
                                    copy=True
                                    )

    @api.constrains('pax_group')
    def check_negative(self):
        for rec in self:
            if rec.pax_group < 0:
                raise UserError(_('Participants must be greater than zero.'))


class DaysValid(models.Model):
    _name = 'days.valid'
    _description = 'Days Valid'

    name = fields.Char('Name')


class GroupCost(models.Model):

    _name = 'group.cost'
    _description = 'Group cost'

    @api.multi
    @api.depends('pax_no', 'no_of_foc')
    def calculate_group_cost(self):
        tansportation_sum = total_cost = visa_sum = hotel_sum = tour_sum = \
            final_foc_cost = meal_sum = guide_sum = ticket_sum = 0.0
        for rec in self:
            if rec.sale_order_id.transaportation_ids:
                if rec.seat_capacity_id:
                    variant_cost = self.cost_for_variants()
                    if rec.seat_capacity_id.id in variant_cost:
                        tansportation_sum = sum([x.rate for x in variant_cost.
                                                 get(rec.seat_capacity_id.id)])
            if rec.pax_no:
                if rec.pax_no != 0:
                    final_transportation_sum = tansportation_sum / rec.pax_no
                    guide_sum = sum([t_rec.price_subtotal for t_rec in rec.
                                     sale_order_id.guide_ids if rec.
                                     sale_order_id.guide_ids]) / rec.pax_no
                    final_foc_cost = rec.foc_cost / rec.pax_no
                if rec.sale_order_id.pax_group != 0:
                    ticket_sum = sum([t_rec.price_subtotal for t_rec in rec.
                                      sale_order_id.ticket_ids if rec.
                                      sale_order_id.ticket_ids]) / rec.\
                        sale_order_id.pax_group
                    meal_sum = sum([t_rec.price_subtotal for t_rec in rec.
                                    sale_order_id.meal_ids if rec.
                                    sale_order_id.meal_ids]) / rec.\
                        sale_order_id.pax_group
                    tour_sum = sum([t_rec.price_subtotal for t_rec in rec.
                                    sale_order_id.tour_ids if rec.
                                    sale_order_id.tour_ids]) / rec.\
                        sale_order_id.pax_group
                if rec.sale_order_id.hotel_ids:
                    hotel_sum = sum([hotel_rec.price_subtotal for hotel_rec in
                                     rec.sale_order_id.hotel_ids if hotel_rec.
                                     room_accupacy_id.
                                     room_selection == 'double'])
                visa_sum = sum([t_rec.price_subtotal for t_rec in rec.
                                sale_order_id.visa_ids if
                                rec.sale_order_id.visa_ids])
                total_cost = (hotel_sum / 2) + ticket_sum + tour_sum + \
                    meal_sum + visa_sum + guide_sum + \
                    final_transportation_sum + \
                    final_foc_cost
                rec.group_cost = total_cost

    @api.multi
    def cost_for_variants(self):
        for rec in self:
            if rec.sale_order_id.transaportation_ids:
                p_dict = {}
                for t_rec in rec.sale_order_id.transaportation_ids:
                    if t_rec.product_id:
                        contract_ids = t_rec.get_contract(
                            'transportation',
                            t_rec.partner_id.id,
                            t_rec.transport_order_id.
                            arrival_date,
                            t_rec.transport_order_id.
                            return_date)
                        if contract_ids:
                            vehicle_ids = self.env['vehical.rates'].search([
                                ('vehicle_contract_id', '=',
                                 contract_ids.ids[0]),
                                ('vehicle_id.name', '=',
                                 t_rec.product_id.name.strip())])
                            for product_rec in vehicle_ids:
                                if p_dict.get(product_rec.vehicle_id.
                                              attribute_value_ids.id, False):
                                    p_dict[product_rec.vehicle_id.
                                           attribute_value_ids.id].append(
                                        product_rec)
                                else:
                                    p_dict[product_rec.vehicle_id.
                                           attribute_value_ids.id] = [
                                        product_rec]
                return p_dict

    @api.multi
    def foc_cost_calculation(self):
        total_foc_cost = hotel_sum = 0.0
        final_transportation_sum = visa_sum = tour_sum = \
            meal_sum = guide_sum = ticket_sum = tansportation_sum = 0.0
        for rec in self:
            if rec.sale_order_id.transaportation_ids:
                if rec.seat_capacity_id:
                    variant_cost = self.cost_for_variants()
                    if rec.seat_capacity_id.id in variant_cost:
                        tansportation_sum = sum([x.rate for x in
                                                 variant_cost.get(
                                                     rec.seat_capacity_id.id)])
            if rec.sale_order_id.hotel_ids:
                hotel_sum = sum([hotel_rec.price_subtotal for hotel_rec in
                                 rec.sale_order_id.hotel_ids if
                                 hotel_rec.room_accupacy_id.room_selection ==
                                 'double'])
            if rec.sale_order_id.visa_ids:
                visa_sum = sum([t_rec.price_subtotal for t_rec in
                                rec.sale_order_id.visa_ids])
            if rec.pax_no != 0:
                final_transportation_sum = tansportation_sum / rec.pax_no
                guide_sum = sum([t_rec.price_subtotal for t_rec in
                                 rec.sale_order_id.guide_ids]) / rec.pax_no
            if rec.sale_order_id.pax_group != 0:
                if rec.sale_order_id.ticket_ids:
                    ticket_sum = sum([t_rec.price_subtotal for t_rec in
                                      rec.sale_order_id.ticket_ids]) / rec.\
                        sale_order_id.pax_group
                meal_sum = sum([t_rec.price_subtotal for t_rec in
                                rec.sale_order_id.meal_ids if
                                rec.sale_order_id.meal_ids]) \
                    / rec.sale_order_id.pax_group
                tour_sum = sum([t_rec.price_subtotal for t_rec in
                                rec.sale_order_id.tour_ids if
                                rec.sale_order_id.tour_ids]) \
                    / rec.sale_order_id.pax_group
            total_foc_cost = hotel_sum + ticket_sum + tour_sum + meal_sum + \
                visa_sum + guide_sum + final_transportation_sum
            rec.foc_cost = total_foc_cost

    @api.multi
    @api.depends('group_cost', 'sale_order_id.fixed_price',
                 'sale_order_id.percent_price')
    def compute_secondary_cost(self):
        for rec in self:
            today = datetime.today()
            usd_grp_cost = rec.sale_order_id.currency_id._convert(
                rec.group_cost, rec.sale_order_id.usd_currency_id,
                rec.sale_order_id.company_id, today)
            if rec.sale_order_id.profit_price == 'fixed':
                rec.usd_group_cost = usd_grp_cost + \
                    rec.sale_order_id.fixed_price
            elif rec.sale_order_id.profit_price == 'percentage':
                rec.usd_group_cost = usd_grp_cost + \
                    (usd_grp_cost * rec.sale_order_id.percent_price / 100)
            else:
                rec.usd_group_cost = usd_grp_cost

    @api.depends('sale_order_id.usd_sgl_supp', 'sale_order_id.usd_per_person')
    def _cal_sngl_supp(self):
        for rec in self:
            rec.sngl_suppl = abs(rec.sale_order_id.usd_per_person -
                                 rec.sale_order_id.usd_sgl_supp)

    pax_no = fields.Integer("Alternative no of PAX ")
    currency_id = fields.Many2one(related="sale_order_id.currency_id")
    secondary_currency_id = fields.Many2one(
        related="sale_order_id.usd_currency_id", string="Secondary Currency")
    no_of_foc = fields.Integer("No of Foc")
    group_cost = fields.Monetary("Group Cost", currency_field='currency_id',
                                 compute='calculate_group_cost')
    usd_group_cost = fields.Monetary(string='Group selling price',
                                     currency_field='secondary_currency_id',
                                     compute="compute_secondary_cost")
    sale_order_id = fields.Many2one('sale.order', "Order", copy=False,
                                    index=True)
    seat_capacity_id = fields.Many2one('product.attribute.value',
                                       "Seat Capacity")
    foc_cost = fields.Float("FOC Cost (Full ROOM)",
                            compute='foc_cost_calculation')
    sngl_suppl = fields.Float("Single Supp", compute="_cal_sngl_supp")
