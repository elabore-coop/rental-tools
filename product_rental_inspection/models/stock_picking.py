# -*- coding: utf-8 -*-

from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_view_inspections(self):
        product_ids = [
            product.product_id.id for product in self.move_ids_without_package
        ]
        ctx = {
            "default_customer_id": self.partner_id.id,
            "default_source_document": self.origin,
            "default_location_id": self.location_id.id,
            "default_phone": self.partner_id.phone,
            "product_list": product_ids,
        }
        return {
            "name": _("Rental Inspection"),
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "rental.product.inspection",
            "type": "ir.actions.act_window",
            "context": ctx,
        }
