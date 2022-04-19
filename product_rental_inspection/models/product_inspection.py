# -*- coding: utf-8 -*-

from datetime import date

from odoo import models, fields, api, _


class RentalProductInspection(models.Model):
    _name = "rental.product.inspection"
    _description = "Product Inspection"
    _rec_name = "ref_number"

    product_id = fields.Many2one("product.product", string="Product")
    ref_number = fields.Char(string="Reference Number", default="New")
    customer_id = fields.Many2one("res.partner", string="Customer")
    location_id = fields.Many2one("stock.location", string="Location")
    phone = fields.Char(string="Phone Number")
    responsible_person_id = fields.Many2one("hr.employee", string="Responsible")
    source_document = fields.Char(string="Source Document")
    date = fields.Datetime(string="Date", default=lambda self: fields.Datetime.now())
    state = fields.Selection(
        [("ready", "Ready"), ("pause", "Paused"), ("done", "Done")], default="ready"
    )
    delayed_line_ids = fields.One2many(
        "product.delayed", "inspection_id", string="Delayed Lines"
    )
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.user.company_id
    )
    total_delayed_amount = fields.Float(string="Delayed Amount", readonly=True)
    total_fuel_charged = fields.Float(string="Fuel Charged Amount")
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id")

    def create_invoice(self):
        inv_obj = self.env["account.move"]
        total_amount = 0
        invoice_line_data = []
        account_id = self.env["account.account"].search(
            [("code", "like", "708000"), ("company_id", "=", self.company_id.id)]
        )
        if not account_id:
            user_type_id = self.env.ref("account.data_account_type_revenue")
            account_id = self.env["account.account"].create(
                {
                    "code": "708000",
                    "name": "Location",
                    "company_id": self.company_id.id,
                    "user_type_id": user_type_id.id,
                }
            )
        for each_delay in self.delayed_line_ids:
            if each_delay.invoice_state == "draft" and each_delay.delayed_amount > 0:
                total_amount += each_delay.delayed_amount
                invoice_line_data.append(
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_id.id,
                            "name": "Delay Charge Invoice " + self.ref_number,
                            "account_id": account_id.id,
                            "price_unit": each_delay.delayed_amount,
                            "quantity": 1,
                        },
                    )
                )
                each_delay.invoice_state = "to_invoice"

        if total_amount > 0:
            invoice = inv_obj.create(
                {
                    "ref": self.ref_number,
                    "invoice_origin": self.ref_number,
                    "partner_id": self.customer_id.id,
                    "move_type": "out_invoice",
                    "invoice_date": date.today(),
                    "invoice_line_ids": invoice_line_data,
                }
            )
            invoice.action_post()

            if invoice:
                return {
                    "name": _("Account Move"),
                    "view_mode": "form",
                    "view_id": self.env.ref("account.view_move_form").id,
                    "view_type": "tree,form",
                    "res_model": "account.move",
                    "type": "ir.actions.act_window",
                    "res_id": invoice.id,
                }

    @api.model
    def default_get(self, vals):
        res = super(RentalProductInspection, self).default_get(vals)
        sequence = self.env["ir.sequence"].next_by_code("product_inspection") or _(
            "Product Inspection"
        )
        if self._context.get("active_model") == "stock.picking":
            res.update(
                {
                    "ref_number": sequence,
                }
            )
        return res

    @api.onchange("customer_id")
    def onchange_filter_product(self):
        if self._context.get("product_list"):
            return {
                "domain": {
                    "product_id": [("id", "in", self._context.get("product_list"))]
                }
            }

    def done(self):
        self.state = "done"

    def pause(self):
        self.state = "pause"

    def resume(self):
        self.state = "ready"


class ProductDelayed(models.Model):
    _name = "product.delayed"
    _description = "Product Delayed"

    inspection_id = fields.Many2one("rental.product.inspection", string="Inspection")
    name = fields.Char(string="Description")
    product_id = fields.Many2one("product.product", string="Product Name")
    delay_cost_per_hour = fields.Float(string="Cost/Hour")
    delayed_hours = fields.Float(string="Total Hours")
    delayed_amount = fields.Float(string="Delayed Amount")
    invoice_state = fields.Selection(
        [("draft", "Draft"), ("to_invoice", "To Invoice")], default="draft"
    )
