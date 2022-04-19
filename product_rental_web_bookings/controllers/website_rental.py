# -*- coding: utf-8 -*-

import json
from datetime import datetime

from odoo import http
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.http import request
from odoo.osv import expression


class WebsiteRental(http.Controller):
    @http.route("/search-product", type="http", auth="public", website=True)
    def search_product(self, **post):
        return request.render(
            "product_rental_bookings.product_search", {"post_data": post}
        )

    def convert_float_to_hh_mm(self, session_id):
        start_date = "{0:02.0f}:{1:02.0f}".format(
            *divmod(session_id.start_time * 60, 60)
        )
        end_date = "{0:02.0f}:{1:02.0f}".format(*divmod(session_id.end_time * 60, 60))
        start_date_fmt = (
            start_date.split(":")[0] + ":" + start_date.split(":")[1] + ":" + "00"
        )
        end_date_fmt = (
            end_date.split(":")[0] + ":" + end_date.split(":")[1] + ":" + "00"
        )
        return start_date_fmt, end_date_fmt

    @http.route("/booking_form", type="http", auth="public", website=True)
    def booking_form(self, **post):
        product_list = []
        if (
            post
            and post.get("based_on")
            and post.get("class_type")
            and post["location"]
        ):
            if post.get("based_on") == "per_session":
                rent_session_id = (
                    request.env["session.config"]
                    .sudo()
                    .browse(int(post.get("session_type")))
                )
                request.session["session_type"] = rent_session_id.name
                request.session["session_type_id"] = rent_session_id.id
                start_date, end_date = self.convert_float_to_hh_mm(rent_session_id)
                date_from = datetime.strptime(
                    post["date_from"] + " " + start_date, "%d-%m-%Y %H:%M:%S"
                )
                date_to = datetime.strptime(
                    post["date_from"] + " " + end_date, "%d-%m-%Y %H:%M:%S"
                )
            else:
                date_format = (
                    "%d-%m-%Y"
                    if post["date_from"] and post["date_to"]
                    else "%d-%m-%Y %H:%M"
                )
                date_from = datetime.strptime(
                    post["date_from"] if post["date_from"] else post["datetime_from"],
                    date_format,
                )
                date_to = datetime.strptime(
                    post["date_to"] + " 23:59:59"
                    if post["date_to"]
                    else post["datetime_to"] + ":00",
                    "%d-%m-%Y %H:%M:%S",
                )
            request.session["date_from"] = date_from
            request.session["date_to"] = date_to
            request.session["location"] = post["location"]
            request.session["class_type"] = post["class_type"]
            request.session["based_on"] = post["based_on"]
            categ_ids = (
                request.env["product.category"]
                .sudo()
                .search([("parent_id", "child_of", int(post["class_type"]))])
            )
            request.env.cr.execute(
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
                    post["location"],
                ),
            )
            product_data = request.env.cr.fetchall()
            if product_data:
                for products in product_data:
                    product = (
                        request.env["product.product"]
                        .sudo()
                        .search([("id", "in", products)])
                    )
                    available_products = (
                        request.env["stock.quant"]
                        .sudo()
                        .search(
                            [
                                ("product_id", "=", product.id),
                                ("quantity", ">", 0),
                                ("location_id", "=", int(post.get("location"))),
                            ]
                        )
                    )
                    if available_products.product_id and product.is_published:
                        product_list.append(available_products.product_id)
                values = {
                    "product_id": product_list,
                    "location": post["location"],
                    "post_data": post,
                }
                return request.render("product_rental_bookings.product_search", values)
            else:
                return request.render(
                    "product_rental_bookings.product_search",
                    {"post_data": post, "error": True},
                )
        else:
            return request.render(
                "product_rental_bookings.product_search", {"post_data": post}
            )

    @http.route(
        '/booking_form/create_quotation/<model("product.product"):product_id>',
        type="http",
        auth="public",
        website=True,
    )
    def create_qutation(self, product_id, **post):
        product_order = {
            "product_id": product_id,
            "post_data": request.session["location"],
        }
        if request.session.get("based_on") in ["per_hour", "per_session"]:
            delta = request.session.get("date_from") - request.session.get("date_to")
            hours = abs(delta.total_seconds() / 3600.0)
            product_order.update({"total_hours": hours})
        return request.render("product_rental_bookings.rental_product", product_order)

    @http.route("/product_cart_update", type="http", auth="public", website=True)
    def product_cart_update(self, **post):
        product_order_list = []
        rental_order_obj = request.env["rental.product.order"]
        order_id = rental_order_obj.search(
            [
                ("customer_name", "=", request.env.user.partner_id.id),
                ("state", "=", "draft"),
            ],
            limit=1,
        )
        if post and post["product_id"]:
            product_id = (
                request.env["product.product"]
                .sudo()
                .search([("id", "=", post["product_id"])])
            )
            enter_hour = post.get("enter_hour")
            if not enter_hour:
                total_day = (
                    request.session.get("date_to") - request.session.get("date_from")
                ).days
                product_order_list.append(
                    (
                        0,
                        0,
                        {
                            "product_id": product_id.id,
                            "price_based": "per_day",
                            "enter_days": total_day + 1,
                            "enter_hour": 0.0,
                            "qty_needed": int(post["qty_needed"]),
                            "price": product_id.rental_amount,
                        },
                    )
                )
            elif enter_hour and request.session["based_on"] == "per_session":
                product_order_list.append(
                    (
                        0,
                        0,
                        {
                            "product_id": product_id.id,
                            "price_based": request.session.get("based_on"),
                            "enter_days": 0.0,
                            "enter_hour": float(post["enter_hour"]),
                            "qty_needed": int(post["qty_needed"]),
                            "price": product_id.rental_amount_per_session,
                        },
                    )
                )
            else:
                product_order_list.append(
                    (
                        0,
                        0,
                        {
                            "product_id": product_id.id,
                            "price_based": request.session.get("based_on"),
                            "enter_days": 0.0,
                            "enter_hour": float(post["enter_hour"]),
                            "qty_needed": int(post["qty_needed"]),
                            "price": product_id.rental_amount_per_hour,
                        },
                    )
                )

            if order_id:
                order_lines_product = []
                for order_line in order_id.product_order_lines_ids:
                    order_lines_product.append(order_line.product_id.id)
                order_id.write(
                    (
                        {
                            "product_order_lines_ids": product_order_list,
                            "is_hours": True
                            if request.session.get("based_on")
                            in ["per_session", "per_hour"]
                            else order_id.is_hours,
                            "is_days": True
                            if request.session.get("based_on") == "per_day"
                            else order_id.is_days,
                        }
                    )
                )
                return request.render(
                    "product_rental_bookings.rental_product_cart_update",
                    {
                        "product_order_id": order_id,
                        "location_id": request.session["location"],
                    },
                )
            else:
                from_date, to_date = rental_order_obj.sudo().start_end_date_global(
                    request.session.get("date_from"), request.session.get("date_to")
                )
                order_id = rental_order_obj.sudo().create(
                    {
                        "customer_name": request.env.user.partner_id.id,
                        "from_date": rental_order_obj.sudo().convert_TZ_UTC(from_date),
                        "to_date": rental_order_obj.sudo().convert_TZ_UTC(to_date),
                        "state": "draft",
                        "is_true": True,
                        "product_order_lines_ids": product_order_list,
                        "location_id": request.session["location"],
                        "is_hours": True
                        if request.session.get("based_on")
                        in ["per_session", "per_hour"]
                        else order_id.is_hours,
                        "is_days": True
                        if request.session.get("based_on") == "per_day"
                        else order_id.is_days,
                    }
                )
            order_id.product_order_lines_ids._get_subtotal()
            request.session["order_id"] = order_id.id
        return request.render(
            "product_rental_bookings.rental_product_cart_update",
            {"product_order_id": order_id, "location_id": request.session["location"]},
        )

    @http.route("/view_cart", type="http", auth="public", website=True)
    def view_cart(self, **post):
        rental_product_order_obj = request.env["rental.product.order"]
        if post:
            order_id = rental_product_order_obj.sudo().search(
                [("id", "=", post["rental_order"])]
            )
        else:
            order_id = rental_product_order_obj.sudo().search(
                [("id", "=", request.session.get("order_id"))]
            )
        request.session["order_id"] = order_id.id
        return request.render(
            "product_rental_bookings.rental_product_cart_update",
            {"product_order_id": order_id},
        )

    def _get_rental_payment_values(self, order, **kwargs):
        values = dict(
            website_rental_order=order,
            errors=[],
            partner=order.customer_name.id,
            order=order,
            payment_action_id=request.env.ref("payment.action_payment_acquirer").id,
            return_url="/rental/payment/validate",
            bootstrap_formatting=True,
        )

        domain = expression.AND(
            [
                [
                    "&",
                    ("state", "in", ["enabled", "test"]),
                    ("company_id", "=", order.company_id.id),
                ],
                [
                    "|",
                    ("country_ids", "=", False),
                    ("country_ids", "in", [order.customer_name.country_id.id]),
                ],
            ]
        )
        acquirers = request.env["payment.acquirer"].search(domain)
        values["acquirers"] = [
            acq
            for acq in acquirers
            if (acq.payment_flow == "form" and acq.view_template_id)
            or (acq.payment_flow == "s2s" and acq.registration_view_template_id)
        ]
        values["tokens"] = request.env["payment.token"].search(
            [
                ("partner_id", "=", order.customer_name.id),
                ("acquirer_id", "in", acquirers.ids),
            ]
        )

        return values

    @http.route(
        "/rental/payment/validate", type="http", auth="public", website=True, csrf=False
    )
    def payment_validate(self, transaction_id=None, rental_order_id=None, **post):
        """Method that should be called by the server when receiving an update
        for a transaction. State at this point :
         - UDPATE ME
        """
        # vals = {}
        outstanding_info = False
        order = (
            request.env["rental.product.order"]
            .sudo()
            .browse(request.session.get("order_id"))
        )
        if order:
            if not order.invoice_ids:
                order.confirm()
            invoice_id = order.contract_ids[0].create_invoice()
            order.contract_ids[0].create_invoice()
            invoices = order.mapped("invoice_ids").filtered(
                lambda inv: inv.state == "posted"
            )
            for inv in invoices:
                if inv.invoice_has_outstanding:
                    outstanding_info = json.loads(
                        inv.invoice_outstanding_credits_debits_widget
                    )
            transaction_id = request.env["payment.transaction"].browse(
                request.session.get("__website_sale_last_tx_id")
            )
            if outstanding_info:
                credit_aml_id = False
                if "content" in outstanding_info:
                    for item in outstanding_info["content"]:
                        credit_aml_id = outstanding_info["content"][0]["id"]
                if credit_aml_id and inv.state == "posted":
                    inv.js_assign_outstanding_line(credit_aml_id)
                assert order.id == request.session.get("order_id")
        return request.render(
            "product_rental_bookings.rental_order_comfirmation", {"order": order}
        )

    @http.route(
        [
            "/rental/payment/transaction/",
            "/rental/payment/transaction/<int:so_id>",
            "/rental/payment/transaction/<int:so_id>/<string:access_token>",
        ],
        type="json",
        auth="public",
        website=True,
    )
    def payment_transaction(
        self,
        acquirer_id,
        save_token=False,
        so_id=None,
        access_token=None,
        token=None,
        **kwargs
    ):
        """Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.

        :param int acquirer_id: id of a payment.acquirer record. If not set the
                                user is redirected to the checkout page
        """
        # Ensure a payment acquirer is selected
        if not acquirer_id:
            return False
        try:
            acquirer_id = int(acquirer_id)
        except:
            return False
        # Retrieve the sale order
        if so_id:
            env = request.env["rental.product.order"]
            domain = [("id", "=", so_id)]
            if access_token:
                env = env.sudo()
                domain.append(("access_token", "=", access_token))
            order = env.search(domain, limit=1)
        else:
            order = (
                request.env["rental.product.order"]
                .sudo()
                .browse(request.session.get("order_id"))
            )
        # Ensure there is something to proceed
        assert order.customer_name.id != request.website.partner_id.id
        # Create transaction
        vals = {
            "acquirer_id": acquirer_id,
            "return_url": "/rental/payment/validate",
            "currency_id": request.env.user.company_id.currency_id.id,
            "amount": order.total_amount,
            "partner_id": order.customer_name.id,
        }
        if save_token:
            vals["type"] = "form_save"
        if token:
            vals["payment_token_id"] = int(token)
        transaction = order._create_payment_transaction(vals)
        last_tx_id = request.session.get("__website_sale_last_tx_id")
        PaymentProcessing.add_payment_transaction(transaction)
        request.session["__website_sale_last_tx_id"] = transaction.id
        return transaction.render_rental_button(order)

    @http.route("/checkout", type="http", auth="public", website=True, csrf=False)
    def checkout(self, **post):
        rental_order_id = (
            request.env["rental.product.order"]
            .sudo()
            .search([("id", "=", request.session.get("order_id"))])
        )
        render_values = self._get_rental_payment_values(rental_order_id, **post)
        if render_values["errors"]:
            render_values.pop("acquirers", "")
            render_values.pop("tokens", "")
        return request.render("product_rental_bookings.checkout_process", render_values)

    @http.route("/get_rate_details", type="json", auth="public", website=True)
    def get_rate_details(self, units, product_id):

        total_day = (
            request.session.get("date_to").date()
            - request.session.get("date_from").date()
        ).days
        product_id = (
            request.env["product.product"].sudo().search([("id", "=", product_id)])
        )
        if units == "per_day":
            product_details = {
                "rate": product_id.rental_amount,
                "total_days": total_day + 1,
                "from_date": request.session.get("date_from"),
                "to_date": request.session.get("date_to"),
            }
            return product_details
        else:
            product_details = {
                "rate": product_id.rental_amount_per_hour
                if units == "per_hour"
                else product_id.rental_amount_per_session,
                "from_date": request.session.get("date_from"),
                "to_date": request.session.get("date_to"),
            }
            return product_details

    @http.route("/product_ordel_line/remove", type="json", auth="user")
    def remove_line(self, order_line_id, **kwrgs):
        line_id = request.env["product.order.line"].browse(int(order_line_id))
        order_id = line_id.product_order_id
        line_id.sudo().unlink()
        if not any(order_id.product_order_lines_ids):
            order_id.sudo().unlink()
        return {"order_id": order_id}

    @http.route("/check/quantity", type="json", auth="public")
    def quantity_check(self, quantity, product_id):
        Product_obj = request.env["product.product"]
        order_line_obj = request.env["product.order.line"]
        product = Product_obj.sudo().search([("id", "=", product_id)])
        rental_order_obj = request.env["rental.product.order"]
        from_date, to_date = rental_order_obj.sudo().start_end_date_global(
            request.session.get("date_from"), request.session.get("date_to")
        )
        start_date = datetime.strptime(
            rental_order_obj.sudo().convert_TZ_UTC(from_date)
            if request.env.user.tz
            else from_date,
            "%Y-%m-%d %H:%M:%S",
        )
        end_date = datetime.strptime(
            rental_order_obj.sudo().convert_TZ_UTC(to_date)
            if request.env.user.tz
            else to_date,
            "%Y-%m-%d %H:%M:%S",
        )
        order_line_ids = order_line_obj.sudo().search(
            [
                ("product_order_id.state", "=", "confirm"),
                ("product_id", "=", product_id),
            ]
        )
        total_in_order_qty = 0
        for order_line in order_line_ids:
            if (
                (start_date <= order_line.product_order_id.from_date <= end_date)
                or (start_date <= order_line.product_order_id.to_date <= end_date)
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
        if product.sudo().qty_available and total_in_order_qty:
            qty_available = product.sudo().qty_available - total_in_order_qty
        else:
            total_in_order_qty = order_line_ids.filtered(
                lambda x: x.qty_needed if x.product_order_id.picking_count > 1 else 0
            )
            qty_available = product.sudo().qty_available + sum(
                total_in_order_qty.mapped("qty_needed")
            )
        total_price_days = product.rental_amount
        total_price_hour = product.rental_amount_per_hour
        if not quantity or not qty_available >= quantity:
            return False
        return {
            "product_price_days": total_price_days,
            "product_price_hour": total_price_hour,
        }
