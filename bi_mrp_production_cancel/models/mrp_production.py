# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import math

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round, float_compare, float_is_zero
from odoo.tools.misc import format_date, OrderedSet


class AccountInvoice_Inherit(models.Model):
    _inherit = "account.move"

    active = fields.Boolean('Active', default=True, track_visibility=True)


class MrpProduction(models.Model):
    """ Manufacturing Orders """
    _inherit = 'mrp.production'

    def post_inventory(self):

        for line in self.finished_move_line_ids :
            line.move_id.write({'mo_price_diff' :line.product_id.standard_price })

        res = super(MrpProduction, self).post_inventory()

        for line in self.finished_move_line_ids :
            line.move_id.write({'mo_price_diff' :line.product_id.standard_price - line.move_id.mo_price_diff })

        return res
    
    def action_cancel(self):
        """ Cancels production order, unfinished stock moves and set procurement
        orders in exception and Cancels production order which is Done."""
        for production in self:
            if production.state == 'done':
                move_obj = self.env['stock.move']
                pick_obj = self.env["stock.picking"]
                if production.move_finished_ids:
                    production.move_finished_ids.with_context(stock_cancel=True)._action_cancel()
                if production.move_raw_ids:
                    production.move_raw_ids.with_context(stock_cancel=True)._action_cancel()
                all_moves = (production.move_finished_ids | production.move_raw_ids)
                # cancel routing picking
                pickings = pick_obj.search([('origin', '=', production.name)])
                if pickings:
                    pick_obj.with_context(stock_cancel=True).action_cancel([x.id for x in pickings])

                for move in all_moves :
                    account_move = self.env['account.move'].sudo().search([('stock_move_id','=',move.id)],order="id desc", limit=1)
                    if account_move :
                        account_move.button_cancel()
                        account_move.write({'active' : False})


                for fg in production.move_finished_ids :
                    if fg.product_id.categ_id.property_cost_method == 'average' :

                        new_std_price = fg.product_id.standard_price - fg.mo_price_diff

                        fg.product_id.with_context(force_company=fg.company_id.id).sudo().write({'standard_price': new_std_price})

            else:
                if any(workorder.state == 'progress' for workorder in self.mapped('workorder_ids')):
                    raise UserError(_('You can not cancel production order, a work order is still in progress.'))
                for production in self:
                    production.workorder_ids.filtered(lambda x: x.state != 'cancel').with_context(stock_cancel=True).action_cancel()

                    finish_moves = production.move_finished_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
                    raw_moves = production.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
                    (finish_moves | raw_moves).with_context(stock_cancel=True)._action_cancel()

            for wo in production.workorder_ids :
                wo.action_cancel()

        self.write({'state': 'cancel', 'is_locked': True})

        return True

    def action_set_to_comfirmed(self):
        """ Cancels production order, unfinished stock moves and set procurement
        orders in exception """
        if not len(self.ids):
            return False
        move_obj = self.env['stock.move']
        for (ids, name) in self.name_get():
            message = _("Manufacturing Order '%s' has been set in confirmed state.") % name
            self.message_post(body = message)
        for production in self:
            all_moves = (production.move_finished_ids | production.move_raw_ids)
            all_moves.sudo().action_draft()
            production.write({'state': 'confirmed'})
        return True


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _should_bypass_reservation(self, forced_location=False):
        self.ensure_one()
        return forced_location.should_bypass_reservation() or self.product_id.type != 'product'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done_or_cancel(self):
        for ml in self:
            if ml.state in ('done', 'cancel'):
                return

    def unlink(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for ml in self:
            if self._context.get('stock_cancel') == True:
                if ml.product_id.type == 'product' and not ml._should_bypass_reservation(ml.location_id) and not float_is_zero(ml.product_qty, precision_digits=precision):
                    self.env['stock.quant']._update_reserved_quantity(ml.product_id, ml.location_id, -ml.product_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id, strict=True)
                if ml.product_id.type == 'product' and not ml._should_bypass_reservation(ml.location_id) and not float_is_zero(ml.product_qty, precision_digits=precision):
                    self.env['stock.quant']._update_reserved_quantity(ml.product_id, ml.location_id, -ml.product_qty, lot_id=ml.lot_id, package_id=ml.package_id, owner_id=ml.owner_id, strict=True)

        moves = self.mapped('move_id')

        if self._context.get('stock_cancel') == True:
            pass 
        else:
            res = super(StockMoveLine,self).unlink()
            return res

        if moves:
            moves.with_prefetch()._recompute_state()

        return models.Model.unlink(self)


class StockMove(models.Model):
    _inherit = 'stock.move'

    mo_price_diff = fields.Float(string='MO Price')

    def action_draft(self):
        for move in self:
            res = move.write({'state': 'waiting'})
            move.with_context(stock_cancel=True)._do_unreserve()
        return res

    def _do_unreserve(self):
        moves_to_unreserve = OrderedSet()
        for move in self:
            if self._context.get('stock_cancel') == True:
                pass
            else:
                if move.state == 'cancel' or (move.state == 'done' and move.scrapped):
                    # We may have cancelled move in an open picking in a "propagate_cancel" scenario.
                    # We may have done move in an open picking in a scrap scenario.
                    continue
                elif move.state == 'done':
                    raise UserError(_("You cannot unreserve a stock move that has been set to 'Done'."))
            moves_to_unreserve.add(move.id)

        moves_to_unreserve = self.env['stock.move'].browse(moves_to_unreserve)

        ml_to_update, ml_to_unlink = OrderedSet(), OrderedSet()
        moves_not_to_recompute = OrderedSet()
        for ml in moves_to_unreserve.move_line_ids:
            if ml.qty_done and not self._context.get('stock_cancel',False) == True:
                ml_to_update.add(ml.id)
            else:
                ml_to_unlink.add(ml.id)
                moves_not_to_recompute.add(ml.move_id.id)
        
        self._recompute_state()

        ml_to_update, ml_to_unlink = self.env['stock.move.line'].browse(ml_to_update), self.env['stock.move.line'].browse(ml_to_unlink)
        moves_not_to_recompute = self.env['stock.move'].browse(moves_not_to_recompute)

        ml_to_update.write({'product_uom_qty': 0})
        ml_to_unlink.with_context(stock_cancel=True).unlink()
        # `write` on `stock.move.line` doesn't call `_recompute_state` (unlike to `unlink`),
        # so it must be called for each move where no move line has been deleted.
        (moves_to_unreserve - moves_not_to_recompute)._recompute_state()
        return True
    

    def _action_cancel(self):
        if not self._context.get('stock_cancel',False) == True:
            if any(move.state == 'done' and not move.scrapped for move in self):
                raise UserError(_('You cannot cancel a stock move that has been set to \'Done\'. Create a return in order to reverse the moves which took place.'))
        moves_to_cancel = self.filtered(lambda m: m.state != 'cancel')
        # self cannot contain moves that are either cancelled or done, therefore we can safely
        # unlink all associated move_line_ids
        moves_to_cancel._do_unreserve()

        for move in moves_to_cancel:
            if  move.stock_valuation_layer_ids:
                move.stock_valuation_layer_ids.sudo().unlink()
                if move.product_id.cost_method in ('average', 'fifo'):
                    last_valuation = self.env['stock.valuation.layer'].search([('product_id', '=', move.product_id.id),('remaining_qty','!=',0.0)], order="id ASC", limit=1)
                    last_valuation.remaining_qty = last_valuation.quantity

            siblings_states = (move.move_dest_ids.mapped('move_orig_ids') - move).mapped('state')
            if move.propagate_cancel:
                # only cancel the next move if all my siblings are also cancelled
                if all(state == 'cancel' for state in siblings_states):
                    move.move_dest_ids.filtered(lambda m: m.state != 'done')._action_cancel()
            else:
                if all(state in ('done', 'cancel') for state in siblings_states):
                    move.move_dest_ids.write({'procure_method': 'make_to_stock'})
                    move.move_dest_ids.write({'move_orig_ids': [(3, move.id, 0)]})
            if move.state == 'done':
                if move.production_id:
                    if move.location_dest_id.usage == 'customer':
                        outgoing_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',move.location_dest_id.id)])
                        stock_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',move.location_id.id)])
                        if outgoing_quant:
                            old_qty = outgoing_quant[0].quantity
                            outgoing_quant[0].quantity = old_qty - move.product_uom_qty
                            abc = outgoing_quant[0].quantity
                        if stock_quant:
                            old_qty = stock_quant[0].quantity
                            stock_quant[0].quantity = old_qty + move.product_uom_qty
                    else:
                        outgoing_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',move.location_id.id)])
                        
                        if outgoing_quant:
                            old_qty = outgoing_quant[0].quantity
                            
                            outgoing_quant[0].quantity = old_qty + move.product_uom_qty
                            
                        outgoing_customer_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',move.location_dest_id.id)])
                        if outgoing_customer_quant:
                            
                            old_qty = outgoing_customer_quant[0].quantity
                            outgoing_customer_quant[0].quantity = old_qty - move.product_uom_qty
                if move.raw_material_production_id:
                    if not move.lot_ids:

                        incoming_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',move.location_dest_id.id)])
                        if incoming_quant:
                            old_qty = incoming_quant[0].quantity
                            incoming_quant[0].quantity = old_qty - move.product_uom_qty
                        incoming_customer_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',move.location_id.id)])
                        if incoming_customer_quant:
                            old_qty = incoming_customer_quant[0].quantity
                            incoming_customer_quant[0].quantity = old_qty + move.product_uom_qty
                    else:
                        for move_id in move:
                            for line in move_id.move_line_ids:
                                if line.lot_id:
                                    if line.product_id.tracking == 'lot':
                                        incoming_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',move.location_dest_id.id),('lot_id','=',line.lot_id.id)])
                                        incoming_customer_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',move.location_id.id),('lot_id','=',line.lot_id.id)])
                                        if incoming_quant:
                                            old_qty = incoming_quant[0].quantity
                                            incoming_quant[0].quantity = old_qty - move.product_uom_qty
                                        if incoming_customer_quant:
                                            old_qty = incoming_customer_quant[0].quantity
                                            incoming_customer_quant[0].quantity = old_qty + move.product_uom_qty
                                    else:
                                        incoming_quant = self.env['stock.quant'].sudo().search([('product_id','=',move.product_id.id),('location_id','=',move.location_id.id),('lot_id','=',line.lot_id.id)])
                                        for lot in incoming_quant:
                                            old_qty = lot.quantity
                                            lot.unlink()
                                            vals = { 'product_id' :move.product_id.id,
                                                     'location_id':move.location_dest_id.id,
                                                     'quantity':  old_qty,
                                                     'lot_id':line.lot_id.id,
                                                   }
                                            test = self.env['stock.quant'].sudo().create(vals)

        self.write({
            'state': 'cancel',
            'move_orig_ids': [(5, 0, 0)],
            'procure_method': 'make_to_stock',
        })
        return True
