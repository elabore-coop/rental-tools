# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductProduct(models.Model):
    _inherit = "product.product"

    is_rental = fields.Boolean(string="Rental", default=False)
    selected_product = fields.Boolean(string="Select", default=False)
    rental_amount = fields.Float(string="Rent Per Day Rate")
    rental_amount_per_hour = fields.Float(string="Rent Per Hour Rate")
    rental_amount_per_session = fields.Float(string="Rent Per Session Rate")
    product_registration_id = fields.Many2one("rental.product.order", string="Order")
    rental_qyt = fields.Float("Quantity", default=1.0)
