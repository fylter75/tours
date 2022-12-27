odoo.define('website_tour_agency.google_map', function (require) {
"use strict";
    var ajax = require('web.ajax');
    var map;
    var infowindow;
    var markersArray = [];
    var pyrmont = new google.maps.LatLng(20.268455824834792, 85.84099235520011);
    var marker;
    var geocoder = new google.maps.Geocoder();
    var infowindow = new google.maps.InfoWindow();

    $(document).ready(function () { 
        $('#allmap').on('shown', function () { 
          google.maps.event.trigger(map, 'resize');
        });
      });
    function initialize() {
        ajax.jsonRpc("/get_all_lat_lang", 'call', {}).then(function(locations) {
            var map = new google.maps.Map(document.getElementById('map'), {
//            		zoom: 2,
                    minZoom: 2,
                    zoom: 6,
                    center: {lat: 24.466667, lng: 54.366669},
//                  center: new google.maps.LatLng(22.43, 73.19),
                    mapTypeId: google.maps.MapTypeId.ROADMAP
            });
            var infowindow = new google.maps.InfoWindow();
            var marker, i;
            for (i = 0; i < locations.length; i++) {
              marker = new google.maps.Marker({
                position: new google.maps.LatLng(locations[i][1], locations[i][2]),
                map: map,
                optimized: false
              });
              google.maps.event.addListener(marker, 'click', (function(marker, i) {
                return function() {	
                  infowindow.setContent(locations[i][0]);
                  infowindow.open(map, marker);
                }
              })(marker, i));
            }
        });
    }
    
    /*google.maps.event.addDomListener(window, 'load', initialize);*/
//    if (window.location.pathname == '/page/hotel'){
//        google.maps.event.addDomListener(window, 'load', initialize);
//    }
    $(document).ready(function(){
    $(document).on('click', '#all_locations', function(){
      initialize();
    });
  });
    
    
    
  function initialize_single_map(company_id) {
      ajax.jsonRpc("/get_single_lat_lang", 'call', {'selected_company_id':company_id}).then(function(locations) {
            var map = new google.maps.Map(document.getElementById('contact_map'+company_id), {
              zoom:6,
              minZoom: 2,
//              draggable: false,
//              center: new google.maps.LatLng(locations[1], locations[2]),
              center: {lat: 24.466667, lng: 54.366669},
              mapTypeId: google.maps.MapTypeId.ROADMAP
            });

            var infowindow = new google.maps.InfoWindow();
            var marker, i;

            marker = new google.maps.Marker({
                position: new google.maps.LatLng(locations[1], locations[2]),
                map: map
              });
            google.maps.event.addListener(marker, 'click', (function(marker, i) {
                return function() {
                  infowindow.setContent(locations[0]);
                  infowindow.open(map, marker);
                }
              })(marker, i));
        });
    }

  $(document).ready(function(){
    $(document).on('click', '#map_single', function(){
      initialize_single_map($(this).data('company_id'))
      google.maps.event.addDomListener(window, 'load', initialize_single_map($('#map_single').data('company_id')));
    });
  });
});
