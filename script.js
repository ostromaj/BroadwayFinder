let allTickets = [];

const cityEl = document.getElementById("city");
const dateEl = document.getElementById("date");
const searchEl = document.getElementById("search");
const resultsEl = document.getElementById("results");
const countEl = document.getElementById("count");
const updatedEl = document.getElementById("updated");

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function money(value) {
  if (value === null || value === undefined || value === "") return "N/A";
  return `$${Number(value).toFixed(0)}`;
}

function render() {
  const city = cityEl.value;
  const date = dateEl.value;
  const q = searchEl.value.trim().toLowerCase();

  let filtered = allTickets.filter(t => {
    const cityMatch = city === "all" || t.city === city;
    const dateMatch = !date || t.date === date;
    const searchMatch = !q || `${t.show} ${t.venue}`.toLowerCase().includes(q);
    return cityMatch && dateMatch && searchMatch;
  });

  filtered.sort((a, b) => Number(a.price || 999999) - Number(b.price || 999999));

  countEl.textContent = filtered.length;

  if (!filtered.length) {
    resultsEl.innerHTML = `<div class="empty">No tickets found for this filter. Try another date or city.</div>`;
    return;
  }

  resultsEl.innerHTML = filtered.map(t => `
    <article class="card">
      <div>
        <div class="show-title">${t.show}</div>
        <div class="meta">
          ${t.city.toUpperCase()} · ${t.venue || "Venue TBD"}<br/>
          ${t.date}${t.time ? ` · ${t.time}` : ""}<br/>
          ${t.section ? `Section: ${t.section}` : "Section not listed"}
        </div>
      </div>
      <div>
        <div class="price">${money(t.price)}</div>
        <div class="source">${t.source}</div>
      </div>
      <a class="button" href="${t.url}" target="_blank" rel="noopener noreferrer">View Ticket</a>
    </article>
  `).join("");
}

async function init() {
  dateEl.value = todayISO();

  try {
    const response = await fetch("data/tickets.json?cacheBust=" + Date.now());
    const payload = await response.json();
    allTickets = payload.tickets || [];
    updatedEl.textContent = `Updated: ${payload.updated_at || "unknown"}`;
    render();
  } catch (err) {
    updatedEl.textContent = "Could not load data";
    resultsEl.innerHTML = `<div class="empty">Could not load ticket data.</div>`;
  }
}

[cityEl, dateEl, searchEl].forEach(el => el.addEventListener("input", render));
init();
