odoo.define('product_rental_bookings.main', function (require) {
    "use strict";
    var ajax = require('web.ajax');

    $(document).ready(function () {

        $('.total_days').hide();
        var error = $('#error').val();
        if (error == "True") {
            $("#myModal").modal();
        }

        $('#date_from').datepicker({
            minDate: new Date(),
            dateFormat: "dd-mm-yy",
            yearRange: new Date().getFullYear().toString() + ':' + new Date().getFullYear().toString(),
            onClose: function (selectedDate) { $("#date_to").datepicker("option", "minDate", selectedDate); }
        });

        $('#date_to').datepicker({
            dateFormat: "dd-mm-yy",
            yearRange: new Date().getFullYear().toString() + ':' + new Date().getFullYear().toString(),
            onClose: function (selectedDate) { $("#date_from").datepicker("option", "maxDate", selectedDate); }
        });

        $('#datetime_from').datetimepicker({
            minDate: new Date(),
            format: 'd-m-Y H:i',
            onClose: function (selectedDate) {
                $("#datetime_to").datetimepicker("option", "minDateTime", selectedDate);
            }
        });

        $('#datetime_to').datetimepicker({
            minDate: new Date(),
            format: 'd-m-Y H:i',
            onClose: function (selectedDate) {
                $("#datetime_from").datetimepicker("option", "maxDateTime", selectedDate);
            }
        });

        $('#datetime_from').on('change', function () {
            var date_from = $('#datetime_from').val()
            var date_to = $('#datetime_to').val()
            if (date_from && date_to && date_from > date_to) {
                alert('From Datetime is after To Datetime')
                $('#datetime_from').val('')
            }
        });

        $('#datetime_to').on('change', function () {
            var date_from = $('#datetime_from').val()
            var date_to = $('#datetime_to').val()
            if (date_from && date_to && date_from > date_to) {
                alert('To Datetime is before From Datetime')
                $('#datetime_to').val('')
            }
        });

        $('.rate_option').click(function () {
            var select_value = $(this).val();
            var qty = $(this).parent().parent().find('.qty').val()
            var hour = $(this).parent().parent().find('.enter_hour').val()
            var day = $(this).parent().parent().find('.total_day').val()
            ajax.jsonRpc('/get_rate_details', 'call', {
                'product_id': $(document).find('.product_id').val(),
                'units': $(this).val(),
            }).then(function (product_details) {
                var rate = parseInt(product_details['rate'])
                var total_day = parseInt(product_details['total_days'])
                var from_date = (product_details['from_date'])
                var to_date = (product_details['to_date'])
                if (select_value == 'per_day') {
                    var html = '';
                    var day = '';
                    $('.total_hour').hide();
                    $('.enter_hour').hide();
                    $('.total_hours').hide();
                    $('.total_day').show();
                    $('.total_days').show();
                    html += "<td>" + rate + "</td>";
                    day += "<td>" + total_day + "</td>"
                    from_date += "<td>" + from_date + "</td>"
                    to_date += "<td>" + to_date + "</td>"
                    $('.rate_value').html(html);
                    $('.total_day').html(day)
                    $('.rate_value').addClass('rate_cls');
                    $('.total_day').addClass('day_cls');
                    $('.date_from').html(from_date)
                    $('.date_to').html(to_date)
                    calculate_total(rate * total_day);
                    $($('.calculate_total')).show()
                    $("input[name='qty_needed']").val(1)
                }
                else if (select_value == 'per_hour') {
                    $('.total_hour').show();
                    $('.enter_hour').show();
                    $('.total_hours').show();
                    $('.total_day').hide();
                    $('.total_days').hide();
                    calculate_total(rate * hour);
                    $($('.calculate_total')).show()
                    $("input[name='qty_needed']").val(1)
                }
                else if (select_value == 'per_session') {
                    $('.total_hour').show();
                    $('.enter_hour').show();
                    $('.total_hours').show();
                    $('.total_day').hide();
                    $('.total_days').hide();
                    calculate_total(rate);
                    $($('.calculate_total')).show()
                    $("input[name='qty_needed']").val(1)
                }

            });
        });
        $(".rate_option").trigger("click");

        $('.quantity').on('change', function () {
            var numberPattern = /\d+/g;
            var rate_value = parseInt($('.rate_cls').html().match(numberPattern));
            var hour = parseInt($('.enter_hour').val());
            var total_day = parseInt($('.day_cls').html().match(numberPattern));
            if ($(this).parent().parent().parent().find('.rate_option').val() == 'per_hour') {
                calculate_total(rate_value * $(this).val() * hour);
            }

        });


        //         const total_amt = $('.calculate_total').html();
        $("input[name='qty_needed']").on('change', function (e) {
            var quantity = e.currentTarget.value;
            var product_id = $("input[name='product_id']").val();
            ajax.jsonRpc('/check/quantity', 'call', {
                'product_id': parseInt(product_id),
                'quantity': parseInt(quantity)
            }).then(function (response) {
                if (response == false) {
                    alert("Quantity Not Available.")
                    e.currentTarget.value = 1;
                }
                else {
                    if ($('.rate_option').val() == 'per_day') {
                        var total_day = ($('.total_day').html().replace('<td>', '')).replace('</td>', '');
                        $('.calculate_total').html(total_day * response.product_price_days * parseInt(quantity))
                    }
                    else {
                        var hour = $("input[name='enter_hour']").val()
                        $('.calculate_total').html(parseInt(hour) * response.product_price_hour * parseInt(quantity))
                    }
                }
                if (e.currentTarget.value == 0) {
                    $(".js_check_product").attr("disabled", true);
                }
                else {
                    $(".js_check_product").attr("disabled", false);
                }
            });
        });

        $('.js_delete_product').click(function () {
            var ele = $(this)
            var id = $(this).attr("id");
            ajax.jsonRpc('/product_ordel_line/remove', 'call', {
                'order_line_id': id,
            }).then(function () {
                ele.closest('tr').remove()
                window.location.reload();
            });
        });

        $('#based_on').click(function () {
            var select_value = $(this).val();
            if (select_value == 'per_hour') {
                $('#session_selection').hide();
                $('#for_hour_selection').show();
                $('#for_day_selection').hide();
                $("#datetime_from").prop("required", true);
                $("#datetime_to").prop("required", true);
                $("#date_from").prop("required", false);
                $("#date_to").prop("required", false);
                $("#session_type").prop("required", false);
                $("#date_from").val('');
                $("#date_to").val('');
            }
            else if (select_value == 'per_day') {
                $('#session_selection').hide();
                $('#for_hour_selection').hide();
                $('#for_day_selection').show();
                $("#to_date").show();
                $("#date_from").prop("required", true);
                $("#date_to").prop("required", true);
                $("#datetime_from").prop("required", false);
                $("#datetime_to").prop("required", false);
                $("#session_type").prop("required", false);
                $("#session_type").val('');
                $("#datetime_from").val('');
                $("#datetime_to").val('');
            }
            else {
                $('#session_selection').show();
                $('#for_hour_selection').hide();
                $('#for_day_selection').show();
                $("#date_from").prop("required", true);
                $("#to_date").hide();
                $("#date_to").prop("required", false);
                $("#datetime_from").prop("required", false);
                $("#datetime_to").prop("required", false);
                $("#datetime_from").val('');
                $("#datetime_to").val('');
            }
        });
    });

    function calculate_total(calculated_value) {
        $('.calculate_total').html("<td>" + calculated_value + "</td>");
    }

});







