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
            throw new Error("خطا در دریافت fars.geojson");
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
        console.error("Fars boundary error:", error);
    });


// ----------------------------------------
// لایه حریق
// ----------------------------------------

const fireLayer = L.layerGroup().addTo(map);

let allFires = [];


// ----------------------------------------
// دریافت CSV
// ----------------------------------------

fetch("data/fires.csv?v=3")
    .then(response => {

        if (!response.ok) {
            throw new Error("fires.csv پیدا نشد");
        }

        return response.text();
    })
    .then(csv => {

        allFires = parseCSV(csv);

        console.log(
            "Total fire records:",
            allFires.length
        );

        showFires("5days");
    })
    .catch(error => {
        console.error("Fire data error:", error);
    });


// ----------------------------------------
// دکمه‌های فیلتر
// ----------------------------------------

document.querySelectorAll(".filter-btn")
    .forEach(button => {

        button.addEventListener("click", () => {

            document
                .querySelectorAll(".filter-btn")
                .forEach(btn => {
                    btn.classList.remove("active");
                });

            button.classList.add("active");

            showFires(
                button.dataset.filter
            );
        });
    });


// ----------------------------------------
// نمایش حریق‌ها
// ----------------------------------------

function showFires(filter) {

    fireLayer.clearLayers();

    let filteredFires = [];


    // ------------------------------------
    // ۵ روز گذشته
    // فعلاً همه داده‌های موجود در CSV
    // ------------------------------------

    if (filter === "5days") {

        filteredFires = allFires.slice();
    }


    // ------------------------------------
    // امروز
    // ------------------------------------

    else if (filter === "today") {

        const today =
            getIranDate(
                new Date()
            );

        filteredFires = allFires.filter(
            fire =>
                fire.acq_date === today
        );
    }


    // ------------------------------------
    // ۲۴ ساعت گذشته
    // ------------------------------------

    else if (filter === "24h") {

        const now =
            new Date();

        const limit =
            now.getTime() -
            (24 * 60 * 60 * 1000);

        filteredFires =
            allFires.filter(
                fire => {

                    const fireDate =
                        parseFireDate(
                            fire
                        );

                    if (!fireDate) {
                        return false;
                    }

                    return (
                        fireDate.getTime() >= limit &&
                        fireDate.getTime() <= now.getTime()
                    );
                }
            );
    }


    // ------------------------------------
    // ایجاد نقاط
    // ------------------------------------

    filteredFires.forEach(fire => {

        const latitude =
            parseFloat(
                fire.latitude
            );

        const longitude =
            parseFloat(
                fire.longitude
            );

        if (
            Number.isNaN(latitude) ||
            Number.isNaN(longitude)
        ) {
            return;
        }


        const marker =
            L.circleMarker(
                [
                    latitude,
                    longitude
                ],
                {
                    radius: 6,
                    color: "#ffffff",
                    weight: 1,
                    fillColor: "#ff2600",
                    fillOpacity: 0.9
                }
            );


        marker.bindPopup(`
            <div dir="rtl">

                <strong>🔥 حریق</strong>

                <br><br>

                تاریخ:
                ${fire.acq_date || "-"}

                <br>

                ساعت:
                ${formatTime(fire.acq_time)}

                <br>

                ماهواره:
                ${fire.sensor || "-"}

                <br>

                اطمینان:
                ${fire.confidence || "-"}

                <br>

                FRP:
                ${fire.frp || "-"}

                <br>

                روز/شب:
                ${fire.daynight || "-"}

            </div>
        `);


        marker.addTo(
            fireLayer
        );
    });


    console.log(
        `Displayed fires: ${filteredFires.length}`
    );
}


// ----------------------------------------
// تبدیل تاریخ و ساعت حریق
// ----------------------------------------

function parseFireDate(fire) {

    if (
        !fire.acq_date ||
        !fire.acq_time
    ) {
        return null;
    }

    const time =
        String(fire.acq_time)
            .trim()
            .replace(":", "")
            .padStart(4, "0");

    const hour =
        parseInt(
            time.substring(0, 2),
            10
        );

    const minute =
        parseInt(
            time.substring(2, 4),
            10
        );

    if (
        Number.isNaN(hour) ||
        Number.isNaN(minute)
    ) {
        return null;
    }

    return new Date(
        `${fire.acq_date}T${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:00Z`
    );
}


// ----------------------------------------
// تاریخ امروز ایران
// ----------------------------------------

function getIranDate(date) {

    return new Intl.DateTimeFormat(
        "en-CA",
        {
            timeZone: "Asia/Tehran",
            year: "numeric",
            month: "2-digit",
            day: "2-digit"
        }
    ).format(date);
}


// ----------------------------------------
// ساعت
// ----------------------------------------

function formatTime(time) {

    if (!time) {
        return "-";
    }

    const value =
        String(time)
            .trim()
            .replace(":", "")
            .padStart(4, "0");

    return (
        value.substring(0, 2) +
        ":" +
        value.substring(2, 4)
    );
}


// ----------------------------------------
// CSV Parser
// ----------------------------------------

function parseCSV(text) {

    const lines =
        text
            .trim()
            .split(/\r?\n/);

    if (lines.length < 2) {
        return [];
    }

    const headers =
        parseCSVLine(
            lines[0]
        );

    return lines
        .slice(1)
        .map(line => {

            const values =
                parseCSVLine(line);

            const row = {};

            headers.forEach(
                (header, index) => {

                    row[
                        header.trim()
                    ] =
                        values[index] !== undefined
                            ? values[index].trim()
                            : "";
                }
            );

            return row;
        });
}


// ----------------------------------------
// CSV line parser
// ----------------------------------------

function parseCSVLine(line) {

    const result = [];

    let current = "";
    let quoted = false;

    for (
        let i = 0;
        i < line.length;
        i++
    ) {

        const char =
            line[i];

        if (char === '"') {
            quoted = !quoted;
            continue;
        }

        if (
            char === "," &&
            !quoted
        ) {

            result.push(
                current
            );

            current = "";

            continue;
        }

        current += char;
    }

    result.push(
        current
    );

    return result;
}
