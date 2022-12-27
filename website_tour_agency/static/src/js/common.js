odoo.define('website_tour_agency.website_tour_agency', function (require) {
"use strict";

    var core = require('web.core');
    var time = require('web.time');

    $(document).ready(function(){
        
        // When choosing an visa, display its required documents
        $("#visa_select").on("change", "select[name='product_id']", function (ev) {
            var payment_id = $(ev.currentTarget).val();
            $('.list_item').addClass("hidden");
            $("#"+payment_id).removeClass("hidden");
        })
        
        $('[data-toggle="tooltip"]').tooltip();
        
        $('.cd-filter-block h4').on('click', function(){
            $(this).toggleClass('closed').siblings('.cd-filter-content').slideToggle(300);
        })
        
       //============ Date Picker ============
        $('.piker-date').datepicker({
            minDate:0,
            icons : {
                time: 'fa fa-clock-o',
                date: 'fa fa-calendar',
                next: 'fa fa-chevron-right',
                previous: 'fa fa-chevron-left',
                up: 'fa fa-chevron-up',
                down: 'fa fa-chevron-down',
               },
            locale : moment.locale(),
            format : time.getLangDateFormat()
        });
         
        
        /* -------------- Number validation ---------------*/
        $(".number").keypress(function (e) {
            //if the letter is not digit then display error and don't type anything
            if (e.which != 8 && e.which != 0 && (e.which < 48 || e.which > 57)) {
               //display error message
                $(this).siblings(".errmsg").html("Digits Only").show().fadeOut("3000");
                return false;
           }
        });
        
        var counter = 1;
        $(".btn-add").on("click", function () {
            var newRow = $("<div>");
            var cols = "";

            cols += '<div class="entry input-group col-xs-3 mt8"><input class="btn" type="file" name="attachment_' + counter + '"/><span class="input-group-btn"><button class="btn ibtnDel" type="button"><span class="fa fa-minus"></span></button></span></div>';
            newRow.append(cols);
            if (counter == 50) $('#addrow').attr('disabled', true).prop('value', "You've reached the limit");
            $("div.controls").append(newRow);
            counter++;
        });
        $("div.controls").on("click", ".ibtnDel", function (event) {
            $(this).closest("div").remove();
            counter -= 1
        });
        
        $(".show-more a").each(function() {
            var $link = $(this);
            var $content = $link.parent().prev("div.text-content");
            var visibleHeight = $content[0].clientHeight;
            var actualHide = $content[0].scrollHeight - 1;

            if (actualHide > visibleHeight) {
                $link.show();
            } else {
                $link.hide();
            }
        });

        $(".show-more a").on("click", function() {
            var $link = $(this);
            var $content = $link.parent().prev("div.text-content");
            var linkText = $link.text();

            $content.toggleClass("short-text, full-text");

            $link.text(getShowLinkText(linkText));

            return false;
        });

        function getShowLinkText(currentText) {
            var newText = '';

            if (currentText.toUpperCase() === "SHOW MORE") {
                newText = "Show less";
            } else {
                newText = "Show more";
            }

            return newText;
        }
        /*FOR FACILITY ICONS*/
        
        $(".show-more-facility a").each(function() {
            var $link = $(this);
            var $content = $link.parent().prev("div.text-content-facility");
            var visibleHeight = $content[0].clientHeight;
            var actualHide = $content[0].scrollHeight - 1;

            if (actualHide > visibleHeight) {
                $link.show();
            } else {
                $link.hide();
            }
        });

        $(".show-more-facility a").on("click", function() {
            var $link = $(this);
            var $content = $link.parent().prev("div.text-content-facility");
            var linkText = $link.text();

            $content.toggleClass("short-text-facility, full-text-facility");

            $link.text(getShowLinkText(linkText));

            return false;
        });

        function getShowLinkText(currentText) {
            var newText = '';

            if (currentText.toUpperCase() === "SHOW MORE") {
                newText = "Show less";
            } else {
                newText = "Show more";
            }

            return newText;
        }
        
        
        /*=================end===================*/
        
        $('#clear_fil').click(function() {
            $('input[name=star]').prop('checked', false);
            window.location.href='/hotels';
        });

        $(".package_carousel").owlCarousel({
            loop:true,
            margin:10,
            nav:true,
            dots:false,
            autoplay:true,
            autoplayTimeout:2500,
            autoplayHoverPause:true,
            responsive:{
                0:{
                    items:1
                },
                600:{
                    items:2
                },
                1000:{
                    items:3
                }
            }
        });

        $('.testimonial_carousel').owlCarousel({
            loop:true,
            margin:10,
            nav:true,
            dots:false,
            autoplay:true,
            autoplayTimeout:2500,
            autoplayHoverPause:true,
            responsive:{
                0:{
                    items:1
                },
                600:{
                    items:2
                },
                1000:{
                    items:2
                }
            }
        });
        
        /*============ Date Validation =============*/
        $('.inquiry_form').submit(function(e){	
                var from = $(".travel_date"),
                     to = $(".return_date"),
                    date_pattern = time.getLangDateFormat(),
                    date_pattern_wo_zero = date_pattern.replace('MM','M').replace('DD','D'),
                    st_date = moment(from.val(), [date_pattern, date_pattern_wo_zero], true),
                    end_date = moment(to.val(), [date_pattern, date_pattern_wo_zero], true),
                    now = new Date();
           now.setHours(0,0,0,0);
           if((!st_date.isValid()) || (!end_date.isValid())){
                var st = st_date.isValid(),
                    et = end_date.isValid();
                if (st){
                    from.removeClass('is-invalid');
                }else{
                    from.addClass('is-invalid');
                }
                if (et){
                    to.removeClass('is-invalid');
                }else{
                    to.addClass('is-invalid');
                }
                alert("Please enter a valid date in the format of " + date_pattern);
                return false;
            }
                else if(Date.parse(from.val()) > Date.parse(to.val())){
                    from.addClass('is-invalid');
                    to.addClass('is-invalid');
                    alert("Return date should be greater than Travel date");
                       return false;
                }else{
                    from.removeClass('is-invalid');
                    to.removeClass('is-invalid');
                    return true;
                }
            });
        
        $(window).scroll(function () {
            $('#back-to-top').tooltip('hide');
                if ($(this).scrollTop() > 50) {
                    $('#back-to-top').fadeIn();
                } else {
                    $('#back-to-top').fadeOut();
                }
        });

        $('#back-to-top').click(function () {
            $('#back-to-top').tooltip('hide');
            $('body,html').animate({
                scrollTop: 0
            }, 800);
            return false;
        });
    });
});
