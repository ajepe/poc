# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import Warning
from odoo.exceptions import UserError


class WizardBatchPayment(models.TransientModel):
    _name = 'wizard.payment.batch'
    _description = 'Batch Payment'

    msg_notify = fields.Char(string='Notify Message', readonly=True)
    amount_total = fields.Float(string='Amount Total', readonly=True)
    sum_partner = fields.Integer(string='Sum Partner', readonly=True)
    invoice_ids = fields.Many2many('account.move', string='Invoices')
    payment_date = fields.Date(string='Payment Date', default=fields.Date.context_today)
    details = fields.Char(string='Details')

    journal_id = fields.Many2one('account.journal', string='Journal',
                                 domain="[('type', 'in', ['bank'])]",
                                 required=True)
    suitable_journal_ids = fields.Many2many('account.journal', compute='_compute_suitable_journal_ids')
    company_id = fields.Many2one(string='Company', store=True, readonly=True,
        related='journal_id.company_id', change_default=True, default=lambda self: self.env.company)
    invoice_filter_type_domain = fields.Char(compute='_compute_invoice_filter_type_domain',
                                             help="Technical field used to have a dynamic domain on journal / taxes in the form view.")



    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        for m in self:
            journal_type = m.invoice_filter_type_domain or 'general'
            domain = [('company_id', '=', m.company_id.id), ('type', '=', journal_type)]
            m.suitable_journal_ids = self.env['account.journal'].search(domain)

    @api.model
    def default_get(self, values):
        data = super(WizardBatchPayment, self).default_get(values)
        invoice_ids = self.env['account.move'].browse(self.env.context.get('active_ids', []))
        if invoice_ids:
            amount_total = float(data.get('amount_total') or 0)
            count_vendor = 0
            list_vendor = []
            list_invoice = []
            for invoice_id in invoice_ids:
                amount_total += invoice_id.amount_total
                if invoice_id.partner_id.id not in list_vendor:
                    count_vendor += 1
                    list_vendor.append(invoice_id.partner_id.id)
                invoice_id.payment_amount = invoice_id.amount_residual_signed
                list_invoice.append(invoice_id.id)
            data.update({
                'amount_total': amount_total,
                'sum_partner': count_vendor,
                'invoice_ids': [(6, 0, list_invoice)] if list_invoice != [] else False,
            })
        return data

    @api.onchange('invoice_ids')
    def onchange_payment_amount(self):
        amount_total = 0
        currency_id = self.env['res.currency'].browse()
        for invoice in self.invoice_ids:
            if abs(invoice.payment_amount) > abs(invoice.amount_residual_signed):
                invoice.payment_amount = abs(invoice.amount_residual_signed)
                raise Warning(_(
                    'Payment amount is must greater than 0 and less than %s.')
                              % invoice.amount_residual_signed)
            else:
                amount_total += abs(invoice.payment_amount)
                currency_id = invoice.currency_id
        if amount_total:
            str_msg_notify = 'You are going to pay %s %s to %s vendors?' % (
                currency_id.symbol or '', amount_total, self.sum_partner)
            self.update({
                'msg_notify': str_msg_notify,
            })
        return {}

    def repair_data(self, invoices):
        dict_invoice = {}
        for invoice in invoices:
            # if invoice.state == 'open':
                list_invoice = []
                if invoice.partner_id.id not in dict_invoice:
                    list_invoice.append(invoice.id)
                    dict_invoice[invoice.partner_id.id] = list_invoice
                else:
                    dict_invoice[invoice.partner_id.id].append(invoice.id)
        return dict_invoice


    def confirm_button(self):
        ctx = self.env.context.copy()
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            move_ids = self.env['account.move'].browse(active_ids)
            batch_id = self.env['account.payment.batch'].create({
                'details': self.details,
                'payment_date': self.payment_date,
                'journal_id': self.journal_id.id,
            })
            for move_id in move_ids:
                payload = {
                    'journal_id': self.journal_id.id,
                    'payment_method_code': self.env['account.payment.method'].search([('payment_type', '=', 'inbound')], limit=1).code,
                    'payment_date': self.payment_date,
                    'communication': self.details,
                    'payment_type': move_id.move_type in ('out_invoice', 'in_refund') and 'inbound' or 'outbound',
                    'amount': move_id.amount_residual,
                    'partner_id': move_id.partner_id.id,
                    'partner_type': move_id.move_type in ('out_invoice', 'out_refund') and 'customer' or 'supplier',
                    'currency_id': move_id.currency_id.id,
                    'group_payment': False,

                }

                payment_register = self.env['account.payment.register'].with_context({'active_ids': move_id.line_ids.ids, 'active_model':'account.move.line'}).create(payload)
                account_payment = payment_register._create_payments()
                account_payment.write({
                    'batch_id': batch_id.id,
                    'communication': self.details,
                })

        view = self.env.ref('hv_batch_payment.batch_payments_form_view')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Registered Batch',
            'res_id': batch_id.id,
            'view_mode': 'form',
            'view_id': view.id,
            'views': [(view.id, 'form')],
            'res_model': 'account.payment.batch',
            'target': 'current',
            'context': ctx,
        }


        # for data in dict_data:
        #     print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!', data)
        #     invoices = self.env['account.move'].browse(dict_data[data])

        #     for invoice in invoices:
        #         communication = ''
        #         pay_amount = 0
        #         if abs(invoice.payment_amount) > abs(invoice.amount_residual_signed):
        #             invoice.payment_amount = abs(invoice.amount_residual_signed)
        #             raise Warning(_(
        #                 'Payment amount is must greater than 0 and less than %s.')
        #                           % invoice.amount_residual_signed)
        #         communication += invoice.move_type in (
        #             'in_invoice', 'in_refund') and invoice.ref or invoice.name + ', '
        #         pay_amount += invoice.payment_amount

        #         # line_invoice_pay = self.env['account.move.line'].search([
        #         #     ('move_id', '=', invoice.id)
        #         # ], limit=1)

        #         payload = {
        #             'journal_id': self.journal_id.id,
        #             'payment_method_code': self.env['account.payment.method'].search([('payment_type', '=', 'inbound')], limit=1).code,
        #             'payment_date': self.payment_date,
        #             'communication': communication,
        #             'payment_type': invoice.move_type in ('out_invoice', 'in_refund') and 'inbound' or 'outbound',
        #             'amount': abs(pay_amount),
        #             'partner_id': self.env['res.partner'].browse(data).id,
        #             'partner_type': invoice.move_type in ('out_invoice', 'out_refund') and 'customer' or 'supplier',
        #             'currency_id': invoice.currency_id.id,
        #             'group_payment': False,
        #             # 'line_ids': line_invoice_pay,
        #             # 'destination_account_id': line_invoice_pay.account_id.id
        #         }

        #         print(payload, '!!!!!!!!!!!!!!!!!!!!!!!!1')

        #         account_payment = payment_register._create_payments()

        #         account_payment.write({
        #             'batch_id': batch_id.id,
        #             'communication': communication,
        #         })

        # view = self.env.ref('hv_batch_payment.batch_payments_form_view')
        # return {
        #     'type': 'ir.actions.act_window',
        #     'name': 'Registered Batch',
        #     'res_id': batch_id.id,
        #     'view_mode': 'form',
        #     'view_id': view.id,
        #     'views': [(view.id, 'form')],
        #     'res_model': 'account.payment.batch',
        #     'target': 'current',
        #     'context': ctx,
        # }
