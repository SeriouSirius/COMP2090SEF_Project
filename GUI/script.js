const appState = {
	userId: null,
	username: "",
	isAdmin: false,
	balance: 0,
	currentView: "auth",
	timers: new Map(),
	refreshScheduled: false,
	lastCreatedEventId: null,
	eventsPage: 1,
	ticketsPage: 1,
	pageSize: 4,
	eventsCache: [],
	ticketsCache: [],
	paymentRefreshPending: false,
};

const authPanel = document.getElementById("auth-panel");
const menuPanel = document.getElementById("menu-panel");
const contentPanel = document.getElementById("content-panel");
const userSummary = document.getElementById("user-summary");
const toast = document.getElementById("toast");

function showToast(message, type = "success") {
	toast.textContent = message;
	toast.className = `toast ${type}`;
	toast.classList.remove("hidden");
	window.setTimeout(() => {
		toast.classList.add("hidden");
	}, 2600);
}

function clearTimers() {
	for (const timerId of appState.timers.values()) {
		clearInterval(timerId);
	}
	appState.timers.clear();
}

function setUserState(userData) {
	appState.userId = userData.user_id;
	appState.username = userData.username;
	appState.isAdmin = Boolean(userData.is_admin);
	appState.balance = Number(userData.balance || 0);
}

function resetUserState() {
	clearTimers();
	closeEventDetailModal();
	appState.userId = null;
	appState.username = "";
	appState.isAdmin = false;
	appState.balance = 0;
	appState.currentView = "auth";
	appState.lastCreatedEventId = null;
	appState.eventsPage = 1;
	appState.ticketsPage = 1;
	appState.eventsCache = [];
	appState.ticketsCache = [];
	appState.paymentRefreshPending = false;
}

function updateUserSummary() {
	if (!appState.userId) {
		userSummary.textContent = "Not logged in";
		return;
	}

	const role = appState.isAdmin ? "Admin" : "Customer";
	userSummary.innerHTML = `<strong>${appState.username}</strong><br>${role} | Balance: ${appState.balance.toFixed(2)}`;
}

function hideAllPanels() {
	authPanel.classList.add("hidden");
	menuPanel.classList.add("hidden");
	contentPanel.classList.add("hidden");
}

function apiErrorMessage(error) {
	return error instanceof Error ? error.message : "Unexpected error";
}

async function apiPost(path, payload = {}) {
	const response = await fetch(path, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify(payload),
	});

	let json = null;
	try {
		json = await response.json();
	} catch (error) {
		throw new Error(`Invalid server response (${response.status})`);
	}

	if (!response.ok || !json.success) {
		throw new Error(json.message || `Request failed (${response.status})`);
	}

	return json;
}

function showAuthView() {
	clearTimers();
	hideAllPanels();
	appState.currentView = "auth";
	authPanel.classList.remove("hidden");
	authPanel.innerHTML = `
		<h2>Auth Menu</h2>
		<p>Login or register to continue.</p>
		<div class="grid-two">
			<form id="login-form" class="stack">
				<h3>Login</h3>
				<div>
					<label for="login-username">Username</label>
					<input id="login-username" name="username" required>
				</div>
				<div>
					<label for="login-password">Password</label>
					<input id="login-password" name="password" type="password" required>
				</div>
				<button type="submit">Login</button>
			</form>
			<form id="register-form" class="stack">
				<h3>Register</h3>
				<div>
					<label for="register-username">Username</label>
					<input id="register-username" name="username" required>
				</div>
				<div>
					<label for="register-password">Password</label>
					<input id="register-password" name="password" type="password" required>
				</div>
				<div>
					<label for="register-payment-pin">Payment PIN (4 digits)</label>
					<input id="register-payment-pin" name="payment_pin" type="password" inputmode="numeric" maxlength="4" required>
				</div>
				<button type="submit">Register</button>
			</form>
		</div>
		<div class="inline-actions" style="margin-top: 0.6rem;">
			<button id="exit-button" type="button" class="secondary">Exit</button>
		</div>
	`;

	document.getElementById("login-form").addEventListener("submit", handleLogin);
	document.getElementById("register-form").addEventListener("submit", handleRegister);
	document.getElementById("exit-button").addEventListener("click", () => {
		showToast("You can close this tab now.", "success");
	});

	updateUserSummary();
}

function showAppView() {
	hideAllPanels();
	menuPanel.classList.remove("hidden");
	contentPanel.classList.remove("hidden");
	renderMainMenu();
	updateUserSummary();
}

function menuButton(action, text) {
	return `<button type="button" data-action="${action}">${text}</button>`;
}

function renderMainMenu() {
	const adminControls = appState.isAdmin
		? `${menuButton("admin-event", "Add events")}${menuButton("admin-bookings", "Check bookings status")}`
		: "";

	menuPanel.innerHTML = `
		<h2>Main Menu</h2>
		<p>Choose a function from the CLI-equivalent options below.</p>
		<div class="menu-list">
			${menuButton("events", "Browse events")}
			${menuButton("balance", "Check balance")}
			${menuButton("tickets", "Check tickets")}
			${menuButton("logout", "Logout")}
			${adminControls}
		</div>
	`;

	menuPanel.querySelectorAll("button[data-action]").forEach((button) => {
		button.addEventListener("click", () => handleMenuAction(button.dataset.action));
	});
}

async function handleLogin(event) {
	event.preventDefault();
	const formData = new FormData(event.target);
	const payload = {
		username: String(formData.get("username") || "").trim(),
		password: String(formData.get("password") || "").trim(),
	};

	try {
		const json = await apiPost("/api/auth/login", payload);
		setUserState(json.data);
		updateUserSummary();
		showAppView();
		showToast(json.message, "success");
		await handleMenuAction("events");
	} catch (error) {
		showToast(apiErrorMessage(error), "error");
	}
}

async function handleRegister(event) {
	event.preventDefault();
	const formData = new FormData(event.target);
	const paymentPin = String(formData.get("payment_pin") || "").trim();
	if (!/^\d{4}$/.test(paymentPin)) {
		showToast("Payment PIN must be exactly 4 digits", "error");
		return;
	}

	const payload = {
		username: String(formData.get("username") || "").trim(),
		password: String(formData.get("password") || "").trim(),
		payment_pin: paymentPin,
	};

	try {
		const json = await apiPost("/api/auth/register", payload);
		setUserState(json.data);
		updateUserSummary();
		showAppView();
		showToast(json.message, "success");
		await handleMenuAction("events");
	} catch (error) {
		showToast(apiErrorMessage(error), "error");
	}
}

async function refreshProfile() {
	if (!appState.userId) {
		return;
	}
	try {
		const json = await apiPost("/api/user/profile", { user_id: appState.userId });
		setUserState(json.data);
		updateUserSummary();
	} catch (error) {
		showToast(apiErrorMessage(error), "error");
	}
}

function renderLoading(title, subtitle) {
	contentPanel.innerHTML = `
		<h2>${title}</h2>
		<p>${subtitle}</p>
	`;
}

function paginateRows(rows, requestedPage) {
	const totalPages = Math.max(1, Math.ceil(rows.length / appState.pageSize));
	const currentPage = Math.min(Math.max(1, requestedPage), totalPages);
	const startIndex = (currentPage - 1) * appState.pageSize;
	return {
		currentPage,
		totalPages,
		pageRows: rows.slice(startIndex, startIndex + appState.pageSize),
	};
}

function paginationMarkup(pageType, currentPage, totalPages) {
	if (totalPages <= 1) {
		return "";
	}

	return `
		<div class="pagination">
			<button type="button" class="secondary" data-page-type="${pageType}" data-page="${currentPage - 1}" ${currentPage <= 1 ? "disabled" : ""}>Previous</button>
			<p class="pagination-info">Page ${currentPage} / ${totalPages}</p>
			<button type="button" class="secondary" data-page-type="${pageType}" data-page="${currentPage + 1}" ${currentPage >= totalPages ? "disabled" : ""}>Next</button>
		</div>
	`;
}

async function handleMenuAction(action) {
	if (!appState.userId && action !== "logout") {
		return;
	}

	closeEventDetailModal();

	switch (action) {
		case "events":
			appState.currentView = "events";
			await loadEventsView();
			break;
		case "balance":
			appState.currentView = "balance";
			await loadBalanceView();
			break;
		case "tickets":
			appState.currentView = "tickets";
			await loadTicketsView();
			break;
		case "admin-event":
			appState.currentView = "admin-event";
			await loadAdminEventView();
			break;
		case "admin-bookings":
			appState.currentView = "admin-bookings";
			await loadAdminBookingStatusView();
			break;
		case "logout":
			await logoutFlow();
			break;
		default:
			showToast("Invalid choice", "error");
	}
}

async function logoutFlow() {
	try {
		if (appState.userId) {
			await apiPost("/api/user/logout", { user_id: appState.userId });
		}
	} catch (error) {
		showToast(apiErrorMessage(error), "error");
	}

	resetUserState();
	showAuthView();
	showToast("Logout success", "success");
}

async function loadEventsView() {
	renderLoading("Browse events", "Loading events...");
	try {
		const json = await apiPost("/api/events/list", { user_id: appState.userId });
		appState.eventsCache = Array.isArray(json.data) ? json.data : [];
		renderEventsPage(appState.eventsPage);
	} catch (error) {
		showToast(apiErrorMessage(error), "error");
		contentPanel.innerHTML = `<h2>Browse events</h2><p class="empty">Failed to load events.</p>`;
	}
}

function renderEventsPage(requestedPage = 1) {
	const events = appState.eventsCache;
	if (!events.length) {
		contentPanel.innerHTML = `
			<h2>Browse events</h2>
			<p class="empty">No events found.</p>
		`;
		return;
	}

	const { currentPage, totalPages, pageRows } = paginateRows(events, requestedPage);
	appState.eventsPage = currentPage;
	const pager = paginationMarkup("events", currentPage, totalPages);

	const cards = pageRows
		.map(
			(eventItem) => `
				<article class="card">
					<div class="card-head">
						<h3>${eventItem.title}</h3>
						<button type="button" data-event-id="${eventItem.event_id}">View detail</button>
					</div>
					<p class="muted">${eventItem.location} | ${eventItem.event_date}</p>
					<p>${eventItem.description}</p>
				</article>
			`
		)
		.join("");

	contentPanel.innerHTML = `
		<h2>Browse events</h2>
		${pager}
		<div class="result-list">${cards}</div>
		${pager}
	`;

	contentPanel.querySelectorAll("button[data-event-id]").forEach((button) => {
		button.addEventListener("click", async () => {
			const eventId = Number(button.dataset.eventId);
			await loadEventDetail(eventId);
		});
	});

	contentPanel.querySelectorAll("button[data-page-type='events']").forEach((button) => {
		button.addEventListener("click", () => {
			const targetPage = Number(button.dataset.page);
			renderEventsPage(targetPage);
		});
	});
}

function closeEventDetailModal() {
	const modal = document.getElementById("event-detail-modal");
	if (modal) {
		modal.remove();
		document.body.classList.remove("modal-open");
	}
}

function openEventDetailModal(eventId, eventData, ticketTypes) {
	closeEventDetailModal();

	const ticketOptionName = `ticket-type-${eventId}`;
	const bookingFormId = `booking-form-${eventId}`;
	const checkoutResultId = `checkout-result-${eventId}`;
	const ticketOptions = ticketTypes
		.map(
			(ticketType) => `
				<label>
					<input type="radio" name="${ticketOptionName}" value="${ticketType.ticket_type_id}" ${ticketType.stock > 0 ? "" : "disabled"}>
					${ticketType.name} | Price: ${Number(ticketType.price).toFixed(2)} | Stock: ${ticketType.stock}
				</label>
			`
		)
		.join("");

	const bookingSection = ticketTypes.length
		? `
			<form id="${bookingFormId}" class="stack">
				<div class="stack">${ticketOptions}</div>
				<div>
					<label for="booking-quantity-${eventId}">Quantity</label>
					<input id="booking-quantity-${eventId}" type="number" min="1" value="1" required>
				</div>
				<button type="submit">Create booking</button>
			</form>
		`
		: `<p class="empty">No ticket types for this event.</p>`;

	const modal = document.createElement("div");
	modal.id = "event-detail-modal";
	modal.className = "modal-overlay";
	modal.innerHTML = `
		<article class="modal-card">
			<div class="modal-header">
				<h3>Event detail</h3>
				<button type="button" class="secondary" id="close-event-modal">Close</button>
			</div>
			<p class="muted">${eventData.location} | ${eventData.event_date}</p>
			<p>${eventData.description}</p>
			${bookingSection}
			<div id="${checkoutResultId}"></div>
		</article>
	`;

	document.body.appendChild(modal);
	document.body.classList.add("modal-open");

	modal.addEventListener("click", (event) => {
		if (event.target === modal) {
			closeEventDetailModal();
		}
	});

	const closeButton = document.getElementById("close-event-modal");
	if (closeButton) {
		closeButton.addEventListener("click", closeEventDetailModal);
	}

	if (ticketTypes.length) {
		document.getElementById(bookingFormId).addEventListener("submit", async (event) => {
			event.preventDefault();
			const selectedTicket = modal.querySelector(`input[name='${ticketOptionName}']:checked`);
			const quantity = Number(document.getElementById(`booking-quantity-${eventId}`).value);

			if (!selectedTicket) {
				showToast("Please choose a ticket type", "error");
				return;
			}
			if (!Number.isInteger(quantity) || quantity <= 0) {
				showToast("Quantity must be a positive integer", "error");
				return;
			}

			await createBooking(eventId, Number(selectedTicket.value), quantity, checkoutResultId);
		});
	}
}

async function loadEventDetail(eventId) {
	try {
		const json = await apiPost("/api/events/detail", {
			user_id: appState.userId,
			event_id: eventId,
		});

		const eventData = json.data.event;
		const ticketTypes = json.data.ticket_types || [];
		openEventDetailModal(eventId, eventData, ticketTypes);
	} catch (error) {
		showToast(apiErrorMessage(error), "error");
	}
}

function formatRemaining(seconds) {
	const safeSeconds = Math.max(0, seconds);
	const minutes = String(Math.floor(safeSeconds / 60)).padStart(2, "0");
	const rem = String(safeSeconds % 60).padStart(2, "0");
	return `${minutes}:${rem}`;
}

function scheduleTicketsRefresh() {
	if (appState.refreshScheduled) {
		return;
	}
	appState.refreshScheduled = true;
	window.setTimeout(async () => {
		appState.refreshScheduled = false;
		if (appState.currentView === "tickets") {
			await loadTicketsView();
		}
	}, 1200);
}

function startCountdown(bookingId, expiresAt, serverNow, node, onExpire) {
	if (!expiresAt || !serverNow || !node) {
		return;
	}

	if (appState.timers.has(bookingId)) {
		clearInterval(appState.timers.get(bookingId));
	}

	const expiresMs = new Date(expiresAt).getTime();
	const serverOffsetMs = new Date(serverNow).getTime() - Date.now();

	const tick = () => {
		const nowMs = Date.now() + serverOffsetMs;
		const remaining = Math.max(0, Math.floor((expiresMs - nowMs) / 1000));
		if (remaining <= 0) {
			node.textContent = "Expired";
			node.classList.add("expired");
			clearInterval(appState.timers.get(bookingId));
			appState.timers.delete(bookingId);
			if (typeof onExpire === "function") {
				onExpire();
			}
			return;
		}

		node.textContent = formatRemaining(remaining);
	};

	tick();
	const timerId = setInterval(tick, 1000);
	appState.timers.set(bookingId, timerId);
}

async function createBooking(eventId, ticketTypeId, quantity, checkoutResultId = "checkout-result") {
	const checkoutResult = document.getElementById(checkoutResultId);
	if (!checkoutResult) {
		return;
	}

	try {
		const json = await apiPost("/api/bookings/create", {
			user_id: appState.userId,
			event_id: eventId,
			ticket_type_id: ticketTypeId,
			quantity,
		});
		const booking = json.data;
		checkoutResult.innerHTML = `
			<div class="card">
				<h3>Checkout</h3>
				<p class="muted">Booking #${booking.id} | Total: ${Number(booking.total_price).toFixed(2)}</p>
				<p>Payment countdown: <span class="countdown" id="checkout-countdown-${booking.id}">--:--</span></p>
				<div>
					<label for="checkout-pin-${booking.id}">Payment PIN</label>
					<input id="checkout-pin-${booking.id}" type="password" inputmode="numeric" maxlength="4" placeholder="4-digit PIN" required>
				</div>
				<div class="inline-actions">
					<button type="button" id="pay-now-${booking.id}">Pay now</button>
				</div>
			</div>
		`;

		const countdownNode = document.getElementById(`checkout-countdown-${booking.id}`);
		const payButton = document.getElementById(`pay-now-${booking.id}`);
		startCountdown(booking.id, booking.expires_at, booking.server_now, countdownNode, () => {
			payButton.disabled = true;
			payButton.textContent = "Expired";
			payButton.classList.add("warn");
		});

		payButton.addEventListener("click", async () => {
			const pinInput = document.getElementById(`checkout-pin-${booking.id}`);
			await payBooking(booking.id, pinInput ? pinInput.value.trim() : "", true);
		});

		showToast(json.message, "success");
	} catch (error) {
		showToast(apiErrorMessage(error), "error");
	}
}

async function payBooking(bookingId, paymentPin, refreshAfter = false) {
	if (!/^\d{4}$/.test(paymentPin)) {
		showToast("Payment PIN must be exactly 4 digits", "error");
		return;
	}

	try {
		const json = await apiPost("/api/bookings/pay", {
			user_id: appState.userId,
			booking_id: bookingId,
			payment_pin: paymentPin,
		});
		appState.balance = Number(json.data.balance || appState.balance);
		updateUserSummary();
		showToast(json.message, "success");
		if (refreshAfter) {
			await refreshProfile();
		}
		await handleMenuAction("tickets");
	} catch (error) {
		showToast(apiErrorMessage(error), "error");
		if (appState.currentView === "tickets") {
			await loadTicketsView();
		}
	}
}

async function loadBalanceView() {
	clearTimers();
	renderLoading("Check balance", "Loading balance...");
	try {
		const balanceJson = await apiPost("/api/balance/get", { user_id: appState.userId });
		appState.balance = Number(balanceJson.data.balance || 0);
		updateUserSummary();

		contentPanel.innerHTML = `
			<h2>Check balance</h2>
			<p>Current balance: <strong>${appState.balance.toFixed(2)}</strong></p>
			<form id="balance-form" class="stack">
				<div>
					<label for="add-amount">Add amount</label>
					<input id="add-amount" type="number" step="0.01" min="0.01" required>
				</div>
				<div>
					<label for="add-balance-pin">Payment PIN</label>
					<input id="add-balance-pin" type="password" inputmode="numeric" maxlength="4" placeholder="4-digit PIN" required>
				</div>
				<button type="submit">Add balance</button>
			</form>
		`;

		document.getElementById("balance-form").addEventListener("submit", async (event) => {
			event.preventDefault();
			const amount = Number(document.getElementById("add-amount").value);
			const paymentPin = document.getElementById("add-balance-pin").value.trim();
			if (!Number.isFinite(amount) || amount <= 0) {
				showToast("Amount must be greater than 0", "error");
				return;
			}
			if (!/^\d{4}$/.test(paymentPin)) {
				showToast("Payment PIN must be exactly 4 digits", "error");
				return;
			}

			try {
				const addJson = await apiPost("/api/balance/add", {
					user_id: appState.userId,
					amount,
					payment_pin: paymentPin,
				});
				appState.balance = Number(addJson.data.new_balance || appState.balance);
				updateUserSummary();
				showToast(addJson.message, "success");
				await loadBalanceView();
			} catch (error) {
				showToast(apiErrorMessage(error), "error");
			}
		});
	} catch (error) {
		showToast(apiErrorMessage(error), "error");
		contentPanel.innerHTML = `<h2>Check balance</h2><p class="empty">Failed to load balance.</p>`;
	}
}

function statusPill(status) {
	const normalized = String(status || "").toLowerCase();
	return `<span class="pill ${normalized}">${normalized || "unknown"}</span>`;
}

function renderTicketQrCode(containerId, qrValue) {
	const container = document.getElementById(containerId);
	if (!container) {
		return;
	}

	container.innerHTML = "";
	if (typeof QRCode === "undefined") {
		container.textContent = "QR generator unavailable.";
		return;
	}

	new QRCode(container, {
		text: qrValue,
		width: 180,
		height: 180,
		colorDark: "#10212f",
		colorLight: "#ffffff",
		correctLevel: QRCode.CorrectLevel.M,
	});
}

async function loadTicketsView() {
	renderLoading("Check tickets", "Loading tickets...");
	try {
		const json = await apiPost("/api/bookings/my", { user_id: appState.userId });
		appState.ticketsCache = Array.isArray(json.data) ? json.data : [];
		renderTicketsPage(appState.ticketsPage);
	} catch (error) {
		showToast(apiErrorMessage(error), "error");
		contentPanel.innerHTML = `<h2>Check tickets</h2><p class="empty">Failed to load tickets.</p>`;
	}
}

function renderTicketsPage(requestedPage = 1) {
	clearTimers();
	const rows = appState.ticketsCache;
	if (!rows.length) {
		contentPanel.innerHTML = `<h2>Check tickets</h2><p class="empty">No tickets bought yet.</p>`;
		return;
	}

	const { currentPage, totalPages, pageRows } = paginateRows(rows, requestedPage);
	appState.ticketsPage = currentPage;
	const pager = paginationMarkup("tickets", currentPage, totalPages);

	const cards = pageRows
		.map(
			(row) => `
				<article class="card" id="booking-${row.id}">
					<div class="card-head">
						<h3>${row.title}</h3>
						${statusPill(row.status)}
					</div>
					<p class="muted">${row.ticket_type_name} | Qty: ${row.quantity} | Total: ${Number(row.total_price).toFixed(2)}</p>
					<p class="muted">${row.location} | ${row.event_date}</p>
					<div class="inline-actions">
						<button type="button" data-detail-id="${row.id}" class="secondary">Detail</button>
						${row.status === "pending" ? `<input type="password" id="pin-${row.id}" inputmode="numeric" maxlength="4" placeholder="Payment PIN">` : ""}
						${row.status === "pending" ? `<button type="button" data-pay-id="${row.id}">Pay now</button>` : ""}
					</div>
					${row.status === "pending" ? `<p>Pay before: <span class="countdown" id="countdown-${row.id}">--:--</span></p>` : ""}
					<div id="detail-${row.id}"></div>
				</article>
			`
		)
		.join("");

	contentPanel.innerHTML = `
		<h2>Check tickets</h2>
		${pager}
		<div class="result-list">${cards}</div>
		${pager}
	`;

	contentPanel.querySelectorAll("button[data-detail-id]").forEach((button) => {
		button.addEventListener("click", async () => {
			const bookingId = Number(button.dataset.detailId);
			await loadTicketDetail(bookingId);
		});
	});

	contentPanel.querySelectorAll("button[data-pay-id]").forEach((button) => {
		button.addEventListener("click", async () => {
			const bookingId = Number(button.dataset.payId);
			const pinInput = document.getElementById(`pin-${bookingId}`);
			await payBooking(bookingId, pinInput ? pinInput.value.trim() : "", true);
		});
	});

	contentPanel.querySelectorAll("button[data-page-type='tickets']").forEach((button) => {
		button.addEventListener("click", () => {
			const targetPage = Number(button.dataset.page);
			renderTicketsPage(targetPage);
		});
	});

	pageRows.filter((row) => row.status === "pending").forEach((row) => {
		const countdownNode = document.getElementById(`countdown-${row.id}`);
		const payButton = contentPanel.querySelector(`button[data-pay-id='${row.id}']`);
		startCountdown(row.id, row.expires_at, row.server_now, countdownNode, () => {
			if (payButton) {
				payButton.disabled = true;
				payButton.textContent = "Expired";
				payButton.classList.add("warn");
			}
			scheduleTicketsRefresh();
		});
	});
}

async function loadTicketDetail(bookingId) {
	const container = document.getElementById(`detail-${bookingId}`);
	if (!container) {
		return;
	}

	container.innerHTML = "<p>Loading detail...</p>";
	try {
		const json = await apiPost("/api/bookings/detail", {
			user_id: appState.userId,
			booking_id: bookingId,
		});
		const row = json.data;
		const verifyUrl = `${window.location.origin}/ticket/verify/${bookingId}`;
		const qrContainerId = `ticket-qr-${bookingId}`;
		container.innerHTML = `
			<div class="card" style="margin-top: 0.5rem;">
				<h3>Ticket detail</h3>
				<p class="muted">${row.description}</p>
				<p class="muted">Location: ${row.location} | Date: ${row.event_date}</p>
				<p class="muted">Ticket Type: ${row.ticket_type_name}</p>
				<div class="qr-wrap">
					<p class="muted"><strong>Ticket QR:</strong> scan to check in.</p>
					<div id="${qrContainerId}" class="qr-code-box"></div>
					<p class="muted qr-hint">QR url: ${verifyUrl}</p>
				</div>
				${row.status === "pending" ? `<p>Expires at: ${row.expires_at}</p>` : ""}
			</div>
		`;
		renderTicketQrCode(qrContainerId, verifyUrl);
	} catch (error) {
		container.innerHTML = `<p class="empty">Failed to load detail.</p>`;
		showToast(apiErrorMessage(error), "error");
	}
}

async function loadAdminEventView() {
	clearTimers();
	contentPanel.innerHTML = `
		<h2>Add events</h2>
		<p>Step 1: create event. Step 2: add ticket types.</p>
		<form id="admin-event-form" class="stack">
			<div>
				<label for="event-title">Title</label>
				<input id="event-title" required>
			</div>
			<div>
				<label for="event-description">Description</label>
				<textarea id="event-description" required></textarea>
			</div>
			<div class="grid-two">
				<div>
					<label for="event-location">Location</label>
					<input id="event-location" required>
				</div>
				<div>
					<label for="event-date">Date and time (YYYY-MM-DD HH:MM)</label>
					<input id="event-date" required>
				</div>
			</div>
			<button type="submit">Create event</button>
		</form>
		<div id="admin-created-event" class="empty" style="margin-top: 0.8rem;">No event created yet.</div>
		<form id="admin-ticket-form" class="stack" style="margin-top: 0.9rem;">
			<div>
				<label for="ticket-event-id">Event ID</label>
				<input id="ticket-event-id" type="number" min="1" required>
			</div>
			<div>
				<label for="ticket-name">Ticket type name</label>
				<input id="ticket-name" required>
			</div>
			<div class="grid-two">
				<div>
					<label for="ticket-price">Ticket price</label>
					<input id="ticket-price" type="number" step="0.01" min="0" required>
				</div>
				<div>
					<label for="ticket-stock">Ticket stock</label>
					<input id="ticket-stock" type="number" min="0" step="1" required>
				</div>
			</div>
			<button type="submit">Add ticket type</button>
		</form>
	`;

	document.getElementById("admin-event-form").addEventListener("submit", async (event) => {
		event.preventDefault();
		const payload = {
			user_id: appState.userId,
			title: document.getElementById("event-title").value.trim(),
			description: document.getElementById("event-description").value.trim(),
			location: document.getElementById("event-location").value.trim(),
			event_date: document.getElementById("event-date").value.trim(),
		};

		try {
			const json = await apiPost("/api/admin/events/add", payload);
			appState.lastCreatedEventId = Number(json.data.event_id);
			const createdNode = document.getElementById("admin-created-event");
			createdNode.textContent = `Event added successfully. Event ID: ${appState.lastCreatedEventId}`;
			document.getElementById("ticket-event-id").value = String(appState.lastCreatedEventId);
			showToast(json.message, "success");
		} catch (error) {
			showToast(apiErrorMessage(error), "error");
		}
	});

	document.getElementById("admin-ticket-form").addEventListener("submit", async (event) => {
		event.preventDefault();
		const eventId = Number(document.getElementById("ticket-event-id").value);
		const price = Number(document.getElementById("ticket-price").value);
		const stock = Number(document.getElementById("ticket-stock").value);
		if (!Number.isInteger(eventId) || eventId <= 0) {
			showToast("Event ID must be a positive integer", "error");
			return;
		}
		if (!Number.isFinite(price) || price < 0 || !Number.isInteger(stock) || stock < 0) {
			showToast("Price and stock must be valid values", "error");
			return;
		}

		const payload = {
			user_id: appState.userId,
			event_id: eventId,
			name: document.getElementById("ticket-name").value.trim(),
			price,
			stock,
		};
		try {
			const json = await apiPost("/api/admin/ticket-types/add", payload);
			showToast(json.message, "success");
			document.getElementById("ticket-name").value = "";
			document.getElementById("ticket-price").value = "";
			document.getElementById("ticket-stock").value = "";
		} catch (error) {
			showToast(apiErrorMessage(error), "error");
		}
	});
}

async function loadAdminBookingStatusView() {
	clearTimers();
	renderLoading("Check bookings status", "Loading booking statuses...");
	try {
		const json = await apiPost("/api/admin/bookings/status", {
			user_id: appState.userId,
		});

		const rows = Array.isArray(json.data) ? json.data : [];
		if (!rows.length) {
			contentPanel.innerHTML = `<h2>Check bookings status</h2><p class="empty">No bookings found.</p>`;
			return;
		}

		const tableRows = rows
			.map(
				(row) => `
					<tr>
						<td>${row.id}</td>
						<td>${row.username}</td>
						<td>${row.title}</td>
						<td>${row.ticket_type_name}</td>
						<td>${row.quantity}</td>
						<td>${Number(row.total_price).toFixed(2)}</td>
						<td>${row.status}</td>
						<td>${row.expires_at || "-"}</td>
					</tr>
				`
			)
			.join("");

		contentPanel.innerHTML = `
			<h2>Check bookings status</h2>
			<div class="table-wrap">
				<table>
					<thead>
						<tr>
							<th>ID</th>
							<th>User</th>
							<th>Event</th>
							<th>Ticket</th>
							<th>Qty</th>
							<th>Total</th>
							<th>Status</th>
							<th>Expires</th>
						</tr>
					</thead>
					<tbody>${tableRows}</tbody>
				</table>
			</div>
		`;
	} catch (error) {
		showToast(apiErrorMessage(error), "error");
		contentPanel.innerHTML = `<h2>Check bookings status</h2><p class="empty">Failed to load booking statuses.</p>`;
	}
}

document.addEventListener("DOMContentLoaded", () => {
	showAuthView();
	document.addEventListener("keydown", (event) => {
		if (event.key === "Escape") {
			closeEventDetailModal();
		}
	});
});
