#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PrintQwebInvoice(models.AbstractModel):

    _name = 'report.tour_travel_package_design.qweb_invoice_package_report1'
    _description = 'qweb invoice package report'

    @api.multi
    def _get_qty(self, lines):
        '''
        To find number of nights
        @param lines: list of records
        '''
        if lines:
            return len(lines) - 1
        else:
            return True

    @api.multi
    def _get_bank_detail(self, data):
        '''
        get the partner's bank details like bank name,address
        and account number.
        @param data: record set
        '''
        partner_bank_obj = self.env['res.partner.bank']
        addr = ''
        partner_bank_id = partner_bank_obj.search([('partner_id', '=',
                                                    data.partner_id.id)],
                                                  limit=1)
        if partner_bank_id.bank_id.street:
            addr += partner_bank_id.bank_id.street + ' '
        if partner_bank_id.bank_id.state:
            addr += partner_bank_id.bank_id.state.name + ','
        if partner_bank_id.bank_id.country:
            addr += partner_bank_id.bank_id.country.code
        return {'bank_name': partner_bank_id.bank_id.name,
                'bank_addr': addr,
                'acc_numner': partner_bank_id.acc_number}

    @api.model
    def _get_report_values(self, docids, data):
        report = self.env['ir.actions.report']._get_report_from_name(
            'tour_travel_package_design.qweb_invoice_package_report')
        inv_ids = self.env['account.invoice'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': inv_ids,
            'data_get': self._get_bank_detail,
            'nights': self._get_qty
        }
