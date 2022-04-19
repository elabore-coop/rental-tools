# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tests import Form


class StockPicking(models.Model):
    _inherit = "stock.picking"

    product_order_rel_id = fields.Many2one(
        "rental.product.order", string="product Order"
    )
    contract_ids = fields.One2many(
        "rental.product.contract", "picking_id", string="Contract Id"
    )
    is_rental = fields.Boolean(string="Rental Move")
    product_move_line_id = fields.One2many(
        "stock.move", "product_move_id", string="Move Lines"
    )
    rental_move_type = fields.Selection(
        [("outgoing", "Customers"), ("incoming", "Return"), ("internal", "Internal")],
        string="Types of Operation",
        required=True,
        default="outgoing",
    )

    def delivery(self):
        move_ids_without_package = []
        if all([each.products_checked for each in self.move_ids_without_package]):
            self.action_confirm()
            self.action_assign()
            res = self.button_validate()
            if isinstance(res, bool):
                pass
            else:
                Form(
                    self.env["stock.immediate.transfer"].with_context(res["context"])
                ).save().process()

            for each in self.move_ids_without_package.filtered(
                lambda l: l.products_checked
            ):
                move_ids_without_package.append(
                    (
                        0,
                        0,
                        {
                            "product_id": each.product_id.id,
                            "products_checked": each.products_checked,
                            "name": each.product_id.name,
                            "product_uom": each.product_uom.id,
                            "product_uom_qty": each.product_uom_qty,
                            "location_id": self.env.ref(
                                "stock.stock_location_customers"
                            ).id,
                            "location_dest_id": each.picking_id.location_id.id,
                        },
                    )
                )

            stock_picking_receipt = self.env["stock.picking"].create(
                {
                    "partner_id": self.partner_id.id,
                    "location_id": self.env.ref("stock.stock_location_customers").id,
                    "rental_move_type": "incoming",
                    "location_dest_id": self.location_id.id,
                    "product_order_rel_id": self.product_order_rel_id.id,
                    "picking_type_id": self.picking_type_id.id,
                    "is_rental": True,
                    "origin": self.origin,
                    "move_ids_without_package": move_ids_without_package,
                }
            )
            stock_picking_receipt.state = "confirmed"
            return stock_picking_receipt
        elif any([each.products_checked for each in self.move_ids_without_package]):
            deliver_move_id = self.copy()
            for each in self.move_ids_without_package:
                if not each.product_id:
                    self.unlink()
            for each in self.product_move_line_id.filtered(
                lambda l: l.products_checked
            ):
                move_ids_without_package.append(
                    (
                        0,
                        0,
                        {
                            "product_id": each.product_id.id,
                            "products_checked": each.products_checked,
                            "name": each.product_id.name,
                            "product_uom_qty": each.product_uom_qty,
                            "product_uom": each.product_uom.id,
                            "location_id": each.picking_id.location_id.id,
                            "location_dest_id": self.env.ref(
                                "stock.stock_location_customers"
                            ).id,
                        },
                    )
                )
                each.unlink()
            deliver_move_id.write(
                {
                    "rental_move_type": "incoming",
                    "state": "confirmed",
                    "move_ids_without_package": move_ids_without_package,
                }
            )
            return deliver_move_id
        else:
            raise UserError(_("Please Select Some Product to Move"))

    def incoming(self):
        self.write({"rental_move_type": "incoming"})
        product_order_id = []
        for each in self.move_ids_without_package:
            product_order_id.append(
                (
                    0,
                    0,
                    {
                        "product_id": each.product_id.id,
                        "products_checked": each.products_checked,
                        "name": each.product_id.name,
                        "product_uom": each.product_uom.id,
                        "location_id": each.picking_id.location_id.id,
                        "location_dest_id": self.env.ref(
                            "stock.stock_location_customers"
                        ).id,
                    },
                )
            )
            self.env["rental.product.logs"].create(
                {
                    "customer_id": self.partner_id.id,
                    "product_id": each.product_id.id,
                    "from_date": self.scheduled_date,
                    "to_date": self.scheduled_date,
                }
            )

        order_id = self.env["rental.product.order"].search(
            [("res_number", "=", self.origin)]
        )
        for each_order in order_id:
            each_order.state = "close"
            each_order.return_date = datetime.now()
        self.state = "assigned"

    def move(self):
        self.state = "done"
        self.action_confirm()
        self.action_assign()
        res = self.button_validate()
        if isinstance(res, bool):
            pass
        else:
            Form(
                self.env["stock.immediate.transfer"].with_context(res["context"])
            ).save().process()
