const map = L.map("map").setView([29.6, 52.5], 7);

L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        attribution: "&copy; OpenStreetMap contributors",
        maxZoom: 18
    }
).addTo(map);


// ----------------------------------------
// مرز فارس
// ----------------------------------------

fetch("fars.geojson")
    .then(response => {
        if (!response.ok) {
            throw new Error("خطا در دریافت مرز فارس");
        }

        return response.json();
    })
    .then(data => {

        const farsLayer = L.geoJSON(data, {
            style: {
                color: "#ff6600",
                weight: 2,
                fill: false
            }
        }).addTo(map);

        const bounds = farsLayer.getBounds();

        if (bounds.isValid()) {
            map.fitBounds(bounds);
        }
    })
    .catch(error => {
        console.error(error);
    });


// ----------------------------------------
// دریافت CSV حریق
// ----------------------------------------

fetch("data/fires.csv")
    .then(response => {
        if (!response.ok) {
            throw new Error("fires.csv پیدا نشد");
        }

        return response.text();
    })
    .then(csv => {

        const rows = parseCSV(csv);

        rows.forEach(fire => {

            const latitude = parseFloat(
                fire.latitude
            );

            const longitude = parseFloat(
                fire.longitude
            );

            if (
                Number.isNaN(latitude) ||
                Number.isNaN(longitude)
            ) {
                return;
            }

            const marker = L.circleMarker(
                [latitude, longitude],
                {
                    radius: 6,
                    color: "#ffffff",
                    weight: 1,
                    fillColor: "#ff2600",
                    fillOpacity: 0.9
                }
            ).addTo(map);


            const date =
                fire.acq_date || "-";

            const time =
                fire.acq_time || "-";

            const satellite =
                fire.sensor || "-";

            const confidence =
                fire.confidence || "-";

            const frp =
                fire.frp || "-";

            const dayNight =
                fire.daynight || "-";


            marker.bindPopup(`
                <div dir="rtl">

                    <strong>🔥 حریق</strong>

                    <br><br>

                    تاریخ: ${date}

                    <br>

                    ساعت: ${time}

                    <br>

                    ماهواره: ${satellite}

                    <br>

                    اطمینان: ${confidence}

                    <br>

                    FRP: ${frp}

                    <br>

                    روز/شب: ${dayNight}

                </div>
            `);
        });

    })
    .catch(error => {
        console.error(error);
    });


// ----------------------------------------
// CSV Parser
// ----------------------------------------

function parseCSV(text) {

    const lines = text
        .trim()
        .split(/\r?\n/);

    if (lines.length < 2) {
        return [];
    }

    const headers = lines[0]
        .split(",")
        .map(header => header.trim());


    return lines.slice(1).map(line => {

        const values = line.split(",");

        const row = {};

        headers.forEach((header, index) => {
            row[header] =
                values[index]
                    ? values[index].trim()
                    : "";
        });

        return row;
    });
}
