# -*- coding: utf-8 -*-

from odoo import models, fields


class StockMove(models.Model):
    _inherit = "stock.move"

    product_move_id = fields.Many2one("stock.picking", string="Product Move")
    products_checked = fields.Boolean(string="Select Products")
