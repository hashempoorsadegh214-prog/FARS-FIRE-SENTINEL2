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
// دریافت CSV فقط یک بار
// ----------------------------------------

fetch("data/fires.csv?v=2")
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

        console.error(
            "Fire data error:",
            error
        );
    });


// ----------------------------------------
// رویداد دکمه‌های فیلتر
// ----------------------------------------

document.querySelectorAll(".filter-btn")
    .forEach(button => {

        button.addEventListener(
            "click",
            () => {

                document
                    .querySelectorAll(".filter-btn")
                    .forEach(btn => {
                        btn.classList.remove("active");
                    });

                button.classList.add("active");

                showFires(
                    button.dataset.filter
                );
            }
        );
    });


// ----------------------------------------
// نمایش حریق‌ها
// ----------------------------------------

function showFires(filter) {

    fireLayer.clearLayers();

    const now = new Date();

    let filtered = [];


    if (filter === "today") {

        const today =
            getIranDate(now);

        filtered = allFires.filter(
            fire =>
                fire.acq_date === today
        );
    }


    else if (filter === "24h") {

        const limit =
            now.getTime() -
            24 * 60 * 60 * 1000;

        filtered = allFires.filter(
            fire => {

                const date =
                    createFireDate(fire);

                return (
                    date &&
                    date.getTime() >= limit
                );
            }
        );
    }


    else {

        const limit =
            now.getTime() -
            5 * 24 * 60 * 60 * 1000;

        filtered = allFires.filter(
            fire => {

                const date =
                    createFireDate(fire);

                return (
                    date &&
                    date.getTime() >= limit
                );
            }
        );
    }


    filtered.forEach(
        fire => {

            const lat =
                parseFloat(
                    fire.latitude
                );

            const lon =
                parseFloat(
                    fire.longitude
                );

            if (
                Number.isNaN(lat) ||
                Number.isNaN(lon)
            ) {
                return;
            }


            const marker =
                L.circleMarker(
                    [lat, lon],
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
                    تاریخ: ${fire.acq_date || "-"}
                    <br>
                    ساعت: ${formatTime(fire.acq_time)}
                    <br>
                    ماهواره: ${fire.sensor || "-"}
                    <br>
                    اطمینان: ${fire.confidence || "-"}
                    <br>
                    FRP: ${fire.frp || "-"}
                    <br>
                    روز/شب: ${fire.daynight || "-"}
                </div>
            `);


            marker.addTo(
                fireLayer
            );
        }
    );


    console.log(
        `${filtered.length} fires displayed`
    );
}


// ----------------------------------------
// ساخت تاریخ حریق
// ----------------------------------------

function createFireDate(fire) {

    if (
        !fire.acq_date ||
        !fire.acq_time
    ) {
        return null;
    }

    const time =
        String(fire.acq_time)
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
// نمایش ساعت
// ----------------------------------------

function formatTime(time) {

    if (!time) {
        return "-";
    }

    const value =
        String(time)
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
        parseCSVLine(lines[0]);

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
// پردازش یک خط CSV
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
