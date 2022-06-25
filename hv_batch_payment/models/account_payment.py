# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'out_receipt': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
    'in_receipt': 'supplier',
}

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    batch_id = fields.Many2one('account.payment.batch', string='Batch Payment')
    payment_date = fields.Date(string='Date', default=fields.Date.context_today, required=True, readonly=True, states={'draft': [('readonly', False)]}, copy=False, tracking=True)
    communication = fields.Char(string='Memo', readonly=True, states={'draft': [('readonly', False)]})
    invoice_ids = fields.Many2many('account.move', 'account_invoice_payment_rel', 'payment_id', 'invoice_id',
                                   string="Invoices", copy=False, readonly=True,
                                   help="""Technical field containing the invoice for which the payment has been generated.
                                       This does not especially correspond to the invoices reconciled with the payment,
                                       as it can have been generated first, and reconciled later""")
