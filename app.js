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
// فیلترها
// ----------------------------------------

const filterControl = L.control({
    position: "topright"
});

filterControl.onAdd = function () {

    const div = L.DomUtil.create(
        "div",
        "fire-filters"
    );

    div.innerHTML = `
        <button data-filter="today">
            امروز
        </button>

        <button data-filter="24h">
            ۲۴ ساعت
        </button>

        <button
            data-filter="5days"
            class="active"
        >
            ۵ روز
        </button>
    `;

    L.DomEvent.disableClickPropagation(div);

    return div;
};

filterControl.addTo(map);


// ----------------------------------------
// لایه حریق‌ها
// ----------------------------------------

const fireLayer = L.layerGroup().addTo(map);

let allFires = [];


// ----------------------------------------
// دریافت CSV
// ----------------------------------------

fetch("data/fires.csv")
    .then(response => {

        if (!response.ok) {
            throw new Error(
                "fires.csv پیدا نشد"
            );
        }

        return response.text();
    })
    .then(csv => {

        allFires = parseCSV(csv);

        showFires("5days");
    })
    .catch(error => {

        console.error(error);

    });


// ----------------------------------------
// نمایش حریق‌ها
// ----------------------------------------

function showFires(filter) {

    fireLayer.clearLayers();

    const now = new Date();

    let filteredFires = [];


    if (filter === "today") {

        const today = getIranDate(now);

        filteredFires = allFires.filter(
            fire => fire.acq_date === today
        );

    }


    else if (filter === "24h") {

        const limit =
            now.getTime() -
            (24 * 60 * 60 * 1000);

        filteredFires = allFires.filter(
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
            (5 * 24 * 60 * 60 * 1000);

        filteredFires = allFires.filter(
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


    filteredFires.forEach(
        fire => {

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

                    ساعت: ${formatTime(time)}

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


            marker.addTo(
                fireLayer
            );
        }
    );


    updateActiveButton(
        filter
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
// تبدیل ساعت FIRMS به HH:MM
// ----------------------------------------

function formatTime(time) {

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
// فعال کردن دکمه انتخاب شده
// ----------------------------------------

function updateActiveButton(filter) {

    document
        .querySelectorAll(
            ".fire-filters button"
        )
        .forEach(button => {

            button.classList.toggle(
                "active",
                button.dataset.filter === filter
            );
        });
}


// ----------------------------------------
// رویداد دکمه‌ها
// ----------------------------------------

document.addEventListener(
    "click",
    event => {

        const button =
            event.target.closest(
                ".fire-filters button"
            );

        if (!button) {
            return;
        }

        showFires(
            button.dataset.filter
        );
    }
);


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
                parseCSVLine(
                    line
                );

            const row = {};

            headers.forEach(
                (header, index) => {

                    row[
                        header.trim()
                    ] =
                        values[index]
                            ? values[index].trim()
                            : "";
                }
            );

            return row;
        });
}


// ----------------------------------------
// CSV Line Parser
// ----------------------------------------

function parseCSVLine(line) {

    const result = [];

    let current = "";
    let insideQuotes = false;


    for (
        let i = 0;
        i < line.length;
        i++
    ) {

        const char =
            line[i];


        if (char === '"') {

            insideQuotes =
                !insideQuotes;

            continue;
        }


        if (
            char === "," &&
            !insideQuotes
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
