// =====================================================
// TOURIST SAFETY SYSTEM
// LOCATION.JS
// Step 4: Live Location Tracking
// Step 5: Nearby Police Stations
// =====================================================


let watchID = null;


// =====================================================
// STEP 4
// START LIVE LOCATION TRACKING
// =====================================================

function startLocationTracking() {

    const status =
        document.getElementById("location-status");


    // Check browser support

    if (!navigator.geolocation) {

        status.innerHTML =
            "❌ Geolocation is not supported by your browser.";

        return;
    }


    status.innerHTML =
        "📍 Requesting location permission...";


    // Start watching location

    watchID = navigator.geolocation.watchPosition(

        function(position) {


            // Get coordinates

            const latitude =
                position.coords.latitude;

            const longitude =
                position.coords.longitude;


            // Show latitude

            document.getElementById(
                "latitude"
            ).innerText =
                latitude.toFixed(6);


            // Show longitude

            document.getElementById(
                "longitude"
            ).innerText =
                longitude.toFixed(6);


            // Status

            status.innerHTML =
                "🟢 Location tracking is active";


            // Send location to Flask

            fetch(
                "/update-location",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body: JSON.stringify({

                        latitude: latitude,

                        longitude: longitude

                    })

                }
            )

            .then(
                response => response.json()
            )

            .then(
                data => {

                    console.log(
                        "Location updated:",
                        data
                    );

                }
            )

            .catch(
                error => {

                    console.error(
                        "Location update error:",
                        error
                    );

                }
            );


        },


        // =================================================
        // LOCATION ERROR
        // =================================================

        function(error) {

            if (error.code === 1) {

                status.innerHTML =
                    "❌ Location permission was denied.";

            }

            else if (error.code === 2) {

                status.innerHTML =
                    "❌ Location is unavailable.";

            }

            else if (error.code === 3) {

                status.innerHTML =
                    "❌ Location request timed out.";

            }

            else {

                status.innerHTML =
                    "❌ Unable to get your location.";

            }

        },


        // =================================================
        // LOCATION OPTIONS
        // =================================================

        {

            enableHighAccuracy: true,

            timeout: 10000,

            maximumAge: 5000

        }

    );

}



// =====================================================
// STOP LIVE LOCATION TRACKING
// =====================================================

function stopLocationTracking() {

    if (watchID !== null) {

        navigator.geolocation.clearWatch(
            watchID
        );

        watchID = null;


        const status =
            document.getElementById(
                "location-status"
            );


        status.innerHTML =
            "⏹️ Location tracking stopped.";

    }

}



// =====================================================
// STEP 5
// FIND NEARBY POLICE STATIONS
// =====================================================

function findNearbyPolice() {

    const status =
        document.getElementById(
            "police-status"
        );


    status.innerHTML =
        "📍 Getting your current location...";


    // Check browser support

    if (!navigator.geolocation) {

        status.innerHTML =
            "❌ Geolocation is not supported.";

        return;
    }


    // Get current position

    navigator.geolocation.getCurrentPosition(

        function(position) {


            const latitude =
                position.coords.latitude;

            const longitude =
                position.coords.longitude;


            status.innerHTML =
                "🔎 Searching nearby police stations...";


            // Send coordinates to Flask

            fetch(
                "/nearby-police",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body: JSON.stringify({

                        latitude: latitude,

                        longitude: longitude

                    })

                }
            )

            .then(
                response => response.json()
            )

            .then(
                data => {


                    // Check server response

                    if (!data.success) {

                        status.innerHTML =
                            "❌ " + data.message;

                        return;
                    }


                    // No stations found

                    if (
                        data.stations.length === 0
                    ) {

                        status.innerHTML =
                            "❌ No police stations found nearby.";

                        return;
                    }


                    // Heading

                    let html =
                        "<h4>👮 Nearby Police Stations</h4>";


                    // Create station list

                    data.stations.forEach(
                        function(station) {


                            // OpenStreetMap URL

                            const mapUrl =
                                "https://www.openstreetmap.org/"
                                + "?mlat="
                                + station.latitude
                                + "&mlon="
                                + station.longitude
                                + "#map=17/"
                                + station.latitude
                                + "/"
                                + station.longitude;


                            html += `

                                <div class="police-item">

                                    <strong>
                                        👮 ${station.name}
                                    </strong>

                                    <br>

                                    <span>
                                        📏
                                        ${station.distance}
                                        km away
                                    </span>

                                    <br>

                                    <a
                                        href="${mapUrl}"
                                        target="_blank"
                                        rel="noopener noreferrer">

                                        🗺️ View on Map

                                    </a>

                                </div>

                            `;

                        }
                    );


                    // Display results

                    status.innerHTML =
                        html;

                }
            )

            .catch(
                error => {

                    console.error(
                        "Police search error:",
                        error
                    );


                    status.innerHTML =
                        "❌ Unable to find nearby police stations.";

                }
            );

        },


        // =================================================
        // LOCATION ERROR
        // =================================================

        function(error) {

            if (error.code === 1) {

                status.innerHTML =
                    "❌ Please allow location access.";

            }

            else if (error.code === 2) {

                status.innerHTML =
                    "❌ Your location is unavailable.";

            }

            else if (error.code === 3) {

                status.innerHTML =
                    "❌ Location request timed out.";

            }

            else {

                status.innerHTML =
                    "❌ Unable to get your location.";

            }

        },


        // =================================================
        // OPTIONS
        // =================================================

        {

            enableHighAccuracy: true,

            timeout: 10000,

            maximumAge: 5000

        }

    );

} 