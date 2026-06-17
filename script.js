let allTickets = [];

const cityEl = document.getElementById("city");
const dateEl = document.getElementById("date");
const searchEl = document.getElementById("search");
const resultsEl = document.getElementById("results");

const ticketCountEl = document.getElementById("ticketCount");
const lastUpdatedEl = document.getElementById("lastUpdated");
const lowestPriceEl = document.getElementById("lowestPrice");
const averagePriceEl = document.getElementById("averagePrice");
const showCountEl = document.getElementById("showCount");
const featuredTicketEl = document.getElementById("featuredTicket");
const todayButton = document.getElementById("todayButton");

const posterImages = [
    "https://images.unsplash.com/photo-1507676184212-d03ab07a01bf?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1514306191717-452ec28c7814?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1460723237483-7a6dc9d0b212?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1585699324551-f6c309eedeca?auto=format&fit=crop&w=900&q=80"
];

function todayISO() {
    return new Date().toISOString().slice(0, 10);
}

function formatMoney(value) {
    if (value === null || value === undefined || value === "") {
        return "N/A";
    }

    return "$" + Number(value).toFixed(0);
}

function getPoster(ticket) {
    if (ticket.image) {
        return ticket.image;
    }

    const text = `${ticket.show || ""}${ticket.venue || ""}`;
    let total = 0;

    for (let i = 0; i < text.length; i++) {
        total += text.charCodeAt(i);
    }

    return posterImages[total % posterImages.length];
}

function getFilteredTickets() {
    const city = cityEl.value;
    const date = dateEl.value;
    const search = searchEl.value.trim().toLowerCase();

    return allTickets
        .filter(ticket => {
            const cityMatch =
                city === "all" ||
                ticket.city === city;

            const dateMatch =
                !date ||
                ticket.date === date;

            const searchMatch =
                !search ||
                `${ticket.show} ${ticket.venue} ${ticket.source}`
                    .toLowerCase()
                    .includes(search);

            return cityMatch && dateMatch && searchMatch;
        })
        .sort((a, b) => {
            return Number(a.price || 999999) - Number(b.price || 999999);
        });
}

function updateStats(tickets) {
    ticketCountEl.textContent = tickets.length;

    if (!tickets.length) {
        lowestPriceEl.textContent = "--";
        averagePriceEl.textContent = "--";
        showCountEl.textContent = "--";
        return;
    }

    const prices = tickets
        .map(ticket => Number(ticket.price))
        .filter(price => !Number.isNaN(price));

    const lowest = Math.min(...prices);
    const average =
        prices.reduce((sum, price) => sum + price, 0) / prices.length;

    const uniqueShows = new Set(
        tickets.map(ticket => ticket.show)
    );

    lowestPriceEl.textContent = formatMoney(lowest);
    averagePriceEl.textContent = formatMoney(average);
    showCountEl.textContent = uniqueShows.size;
}

function updateFeaturedTicket(tickets) {
    if (!tickets.length) {
        featuredTicketEl.innerHTML = `
            <div class="featured-label">
                Cheapest Ticket Right Now
            </div>

            <div class="featured-loading">
                No tickets found for this filter.
            </div>
        `;
        return;
    }

    const ticket = tickets[0];

    featuredTicketEl.innerHTML = `
        <div class="featured-label">
            Cheapest Ticket Right Now
        </div>

        <img
            src="${getPoster(ticket)}"
            alt="${ticket.show}"
            style="
                width:100%;
                height:120px;
                object-fit:cover;
                border-radius:16px;
                margin-bottom:16px;
            "
        >

        <a
            href="${ticket.url}"
            target="_blank"
            class="ticket-title"
        >
            ${ticket.show}
        </a>

        <div style="color:#cbd5e1;margin-top:8px;">
            ${ticket.venue || "Venue TBD"}
        </div>

        <div style="font-size:2rem;font-weight:bold;margin-top:14px;color:#22c55e;">
            ${formatMoney(ticket.price)}
        </div>

        <a
            href="${ticket.url}"
            target="_blank"
            class="view-button"
            style="display:inline-block;margin-top:12px;"
        >
            View Cheapest Deal →
        </a>
    `;
}

function renderTicketCard(ticket) {
    const template = document.getElementById("ticketTemplate");
    const card = template.content.cloneNode(true);

    const ticketCard = card.querySelector(".ticket-card");
    const image = card.querySelector(".ticket-image");
    const priceBadge = card.querySelector(".ticket-price-badge");
    const title = card.querySelector(".ticket-title");
    const meta = card.querySelector(".ticket-meta");
    const tags = card.querySelectorAll(".tag");
    const source = card.querySelector(".ticket-source");
    const viewButton = card.querySelector(".view-button");

    ticketCard.addEventListener("click", event => {
        if (event.target.tagName.toLowerCase() !== "a") {
            window.open(ticket.url, "_blank");
        }
    });

    image.src = getPoster(ticket);
    image.alt = ticket.show;

    priceBadge.textContent = formatMoney(ticket.price);

    title.textContent = ticket.show || "Unknown Show";
    title.href = ticket.url || "#";

    meta.textContent = ticket.venue || "Venue TBD";

    tags[0].textContent = (ticket.city || "city").toUpperCase();
    tags[1].textContent = ticket.section || "Best Available";
    tags[2].textContent = ticket.time || ticket.date || "Time TBD";

    source.textContent = ticket.source || "Unknown source";

    viewButton.href = ticket.url || "#";

    resultsEl.appendChild(card);
}

function render() {
    const tickets = getFilteredTickets();

    resultsEl.innerHTML = "";

    updateStats(tickets);
    updateFeaturedTicket(tickets);

    if (!tickets.length) {
        resultsEl.innerHTML = `
            <div style="
                grid-column:1/-1;
                background:rgba(255,255,255,.05);
                border:1px solid rgba(255,255,255,.08);
                padding:40px;
                border-radius:24px;
                text-align:center;
                color:#cbd5e1;
            ">
                No tickets found. Try changing the date, city, or search.
            </div>
        `;
        return;
    }

    tickets.forEach(renderTicketCard);
}

async function loadTickets() {
    dateEl.value = todayISO();

    try {
        const response = await fetch("data/tickets.json?cacheBust=" + Date.now());
        const payload = await response.json();

        allTickets = payload.tickets || [];

        lastUpdatedEl.textContent =
            "Last updated: " + (payload.updated_at || "unknown");

        render();

    } catch (error) {
        console.error(error);

        lastUpdatedEl.textContent = "Could not load ticket data.";

        resultsEl.innerHTML = `
            <div style="
                grid-column:1/-1;
                background:rgba(255,255,255,.05);
                border:1px solid rgba(255,255,255,.08);
                padding:40px;
                border-radius:24px;
                text-align:center;
                color:#cbd5e1;
            ">
                Could not load ticket data. Make sure data/tickets.json exists.
            </div>
        `;
    }
}

cityEl.addEventListener("input", render);
dateEl.addEventListener("input", render);
searchEl.addEventListener("input", render);

todayButton.addEventListener("click", () => {
    dateEl.value = todayISO();
    render();

    document
        .getElementById("ticket-board")
        .scrollIntoView({ behavior: "smooth" });
});

loadTickets();
