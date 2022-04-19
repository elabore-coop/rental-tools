# -*- coding: utf-8 -*-

from datetime import datetime, date

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError


class ProductBooking(models.TransientModel):
    _name = "product.booking"
    _rec_name = "book_number"
    _description = "Book"

    @api.depends(
        "product_line_ids",
        "total_days",
        "extra_charges",
        "price_based",
        "from_date",
        "to_date",
    )
    def compute_rate(self):
        for record in self:
            record.total = 0
            record.sub_total = 0
            record.total_days = 0
            record.total_hours = 0
            if record.from_date and record.to_date:
                date_from = datetime.strptime(
                    str(record.from_date), "%Y-%m-%d %H:%M:%S"
                )
                date_to = datetime.strptime(str(record.to_date), "%Y-%m-%d %H:%M:%S")
                delta = date_from - date_to
                record.total_days = abs(delta.days)
                record.total_hours = abs(delta.total_seconds() / 3600.0)
            sub_total = 0.0
            with_tax_total = 0.0
            for product in record.product_line_ids.filtered(
                lambda fv: fv.selected_product
            ):
                if record.price_based == "per_day":
                    taxes = product.taxes_id.compute_all(
                        product.rental_qyt,
                        product.currency_id,
                        product.rental_amount * record.total_days,
                    )
                    sub_total += taxes["total_excluded"]
                    with_tax_total += taxes["total_included"]
                elif record.price_based == "per_hour":
                    taxes = product.taxes_id.compute_all(
                        product.rental_qyt,
                        product.currency_id,
                        product.rental_amount_per_hour * record.total_hours,
                    )
                    sub_total += taxes["total_excluded"]
                    with_tax_total += taxes["total_included"]
                else:
                    taxes = product.taxes_id.compute_all(
                        product.rental_qyt,
                        product.currency_id,
                        product.rental_amount_per_session,
                    )
                    sub_total += taxes["total_excluded"]
                    with_tax_total += taxes["total_included"]
            record.sub_total = sub_total
            record.total = with_tax_total + record.extra_charges

    @api.model
    def _get_based_on_selections(self):
        enabled_day_rent = (
            self.env["ir.config_parameter"].sudo().get_param("enabled_day_rent")
        )
        enabled_hour_rent = (
            self.env["ir.config_parameter"].sudo().get_param("enabled_hour_rent")
        )
        enabled_session_rent = (
            self.env["ir.config_parameter"].sudo().get_param("enabled_session_rent")
        )
        selection = []
        if enabled_day_rent:
            selection.append(("per_day", "Day"))
        if enabled_hour_rent:
            selection.append(("per_hour", "Hour"))
        if enabled_session_rent:
            selection.append(("per_session", "Session"))
        return selection

    book_number = fields.Char(string="Book Number")
    from_date = fields.Datetime(string="From Date")
    to_date = fields.Datetime(string="To Date")
    product_line_ids = fields.Many2many(
        "product.product",
        "product_search_table",
        "product_search_id",
        "product_book_id",
        string="Available Product",
    )
    is_search = fields.Boolean(string="Is Search", default=False)
    total_days = fields.Float(string="Total Days", compute="compute_rate")
    extra_charges = fields.Monetary(string="Extra Charges")
    sub_total = fields.Float(string="Sub Total(Exclusive Tax)", compute="compute_rate")
    total = fields.Float(string="Total", compute="compute_rate")
    categ_id = fields.Many2one(
        "product.category", required=True, string="Product Category"
    )
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.user.company_id
    )
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id")
    location_id = fields.Many2one("stock.location", string="Location")
    price_based = fields.Selection(
        selection=_get_based_on_selections, default="per_day", string="Based On"
    )
    total_hours = fields.Float(string="Total Hours", compute="compute_rate")
    session_id = fields.Many2one("session.config", string="Session")

    @api.constrains("from_date", "to_date")
    def check_date(self):
        for record in self:
            if (
                date.strftime(
                    datetime.strptime(str(record.from_date), "%Y-%m-%d %H:%M:%S"),
                    "%Y-%m-%d",
                )
                < str(date.today())
            ):
                raise ValidationError(_("You cannot enter past date"))
            if date.strftime(
                datetime.strptime(str(record.to_date), "%Y-%m-%d %H:%M:%S"), "%Y-%m-%d"
            ) < str(date.today()):
                raise ValidationError(_("You cannot enter past date"))

    @api.model
    def convert_float_to_hh_mm(self, session_id, from_date):
        start_date = "{0:02.0f}:{1:02.0f}".format(
            *divmod(session_id.start_time * 60, 60)
        )
        end_date = "{0:02.0f}:{1:02.0f}".format(*divmod(session_id.end_time * 60, 60))
        start_date_fmt = (
            "%Y-%m-%d "
            + start_date.split(":")[0]
            + ":"
            + start_date.split(":")[1]
            + ":"
            + "00"
        )
        end_date_fmt = (
            "%Y-%m-%d "
            + end_date.split(":")[0]
            + ":"
            + end_date.split(":")[1]
            + ":"
            + "00"
        )
        start_str_datetime = from_date.strftime(start_date_fmt)
        end_str_datetime = from_date.strftime(end_date_fmt)
        start_date = self.env["rental.product.order"].convert_TZ_UTC(start_str_datetime)
        end_date = self.env["rental.product.order"].convert_TZ_UTC(end_str_datetime)
        return start_date, end_date

    @api.onchange("price_based", "from_date", "session_id")
    def onchange_date_from_price_based(self):
        if self.price_based == "per_session" and self.from_date and self.session_id:
            start_time, end_time = self.convert_float_to_hh_mm(
                self.session_id, self.from_date
            )
            self.to_date = end_time
            self.from_date = start_time

    @api.model
    def create(self, vals):
        vals.update(
            {
                "book_number": self.env["ir.sequence"].next_by_code("product_booking")
                or _("Product Booking")
            }
        )
        return super(ProductBooking, self).create(vals)

    def search_product(self):
        product_id = []
        if self.from_date and self.to_date:
            if self.from_date > self.to_date:
                raise ValidationError("To Date must be greater than From date")
            elif not self.env.user.has_group("stock.group_stock_multi_locations"):
                raise AccessError(
                    _("Manage Multiple Stock Locations need to be assign.")
                )
            else:
                categ_ids = self.env["product.category"].search(
                    [("parent_id", "child_of", self.categ_id.id)]
                )
                self.env.cr.execute(
                    """
                    SELECT 
                        propro.id 
                    FROM product_product propro
                    JOIN product_template protmp ON protmp.id = propro.product_tmpl_id
                    WHERE 
                        protmp.categ_id IN %s AND
                        propro.is_rental='t' AND
                        propro.id IN (
                            Select product_id from stock_quant where location_id = %s);                
                """,
                    (
                        tuple(categ_ids.ids),
                        self.location_id.id,
                    ),
                )
                product_data = self.env.cr.fetchall()
                if product_data:
                    for products in product_data:
                        product = (
                            self.env["product.product"]
                            .sudo()
                            .search([("id", "in", products)])
                        )
                        available_product_stock = self.env["stock.quant"].search(
                            [
                                ("product_id", "=", product.id),
                                ("quantity", ">", 0),
                                ("location_id", "=", self.location_id.id),
                            ]
                        )
                        available_product_stock.product_id.rental_qyt = 1.0
                        available_product_stock.product_id.selected_product = False
                        product_id.extend(available_product_stock.product_id.ids)
                    self.update(
                        {
                            "product_line_ids": [(6, 0, product_id)],
                            "total": self.total,
                            "is_search": True,
                        }
                    )
                else:
                    raise ValidationError("Sorry!!! No any Product Available!!!")

    def book_product(self):
        product = False
        for product_line in self.product_line_ids:
            if product_line.selected_product:
                product = True
        if product:
            product_order_id = []
            for product_id in self.product_line_ids.filtered(
                lambda fv: fv.selected_product
            ):
                # available_product_stock = self.env['stock.quant'].search([('product_id', '=', product_id.id),
                #                                                           ('location_id', '=',
                #                                                            self.location_id.id)])
                # if product_id.rental_qyt > available_product_stock.quantity:
                #     raise ValidationError(_('Available quantity for %s is %d') % (product_id.name,
                #                                                                   available_product_stock.quantity))
                order_line_obj = self.env["product.order.line"]
                start_date = self.from_date
                end_date = self.to_date
                order_line_ids = order_line_obj.sudo().search(
                    [
                        ("product_order_id.state", "=", "confirm"),
                        ("product_id", "=", product_id.id),
                    ]
                )
                total_in_order_qty = 0
                for order_line in order_line_ids:
                    if (
                        (
                            start_date
                            <= order_line.product_order_id.from_date
                            <= end_date
                        )
                        or (
                            start_date
                            <= order_line.product_order_id.to_date
                            <= end_date
                        )
                        and order_line.product_order_id.picking_count == 1
                    ):
                        total_in_order_qty += (
                            order_line.qty_needed
                            if order_line.product_order_id.picking_count == 1
                            else 0
                        )
                    elif (
                        (
                            order_line.product_order_id.from_date
                            <= start_date
                            <= order_line.product_order_id.to_date
                        )
                        or (
                            order_line.product_order_id.from_date
                            <= end_date
                            <= order_line.product_order_id.to_date
                        )
                        and order_line.product_order_id.picking_count == 1
                    ):
                        total_in_order_qty += (
                            order_line.qty_needed
                            if order_line.product_order_id.picking_count == 1
                            else 0
                        )
                if product_id.sudo().qty_available and total_in_order_qty:
                    qty_available = product_id.sudo().qty_available - total_in_order_qty
                else:
                    total_in_order_qty = order_line_ids.filtered(
                        lambda x: x.qty_needed
                        if x.product_order_id.picking_count > 1
                        else 0
                    )
                    qty_available = product_id.sudo().qty_available + sum(
                        total_in_order_qty.mapped("qty_needed")
                    )
                if (
                    not product_id.rental_qyt
                    or not qty_available >= product_id.rental_qyt
                ):
                    raise ValidationError(
                        _("Available quantity for %s is %d")
                        % (product_id.name, qty_available)
                    )
                else:
                    if self.price_based == "per_day":
                        rate_total = product_id.rental_amount
                    else:
                        if self.price_based == "per_hour":
                            rate_total = product_id.rental_amount_per_hour
                        else:
                            rate_total = product_id.rental_amount_per_session
                    product_order_id.append(
                        (
                            0,
                            0,
                            {
                                "product_id": product_id.id,
                                "name": product_id.name,
                                "price_based": self.price_based,
                                "enter_days": self.total_days
                                if self.price_based == "per_day"
                                else 0,
                                "enter_hour": self.total_hours
                                if self.price_based in ["per_hour", "per_session"]
                                else 0,
                                "price": rate_total,
                                "qty_needed": product_id.rental_qyt,
                                "tax_id": [(6, 0, product_id.taxes_id.ids)],
                            },
                        )
                    )
            return {
                "name": "product order",
                "view_type": "form",
                "view_mode": "form",
                "res_model": "rental.product.order",
                "type": "ir.actions.act_window",
                "context": {
                    "default_from_date": self.from_date,
                    "default_to_date": self.to_date,
                    "default_extra_charges": self.extra_charges,
                    "default_is_days": True if self.price_based == "per_day" else False,
                    "default_is_hours": True
                    if self.price_based in ["per_hour", "per_session"]
                    else False,
                    "default_product_order_lines_ids": product_order_id,
                    "default_location_id": self.location_id.id,
                    "default_price_based": self.price_based,
                },
            }
        else:
            raise ValidationError(_("First Please Select the Product"))
