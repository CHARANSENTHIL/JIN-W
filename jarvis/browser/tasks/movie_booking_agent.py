"""
JARVIS Movie Booking Agent — BookMyShow / PVR automation.
ALWAYS pauses before payment for user confirmation.
"""
import time
from jarvis.browser.browser_controller import BrowserController

# Supported booking sites
BOOKING_SITES = {
    "bookmyshow": "https://in.bookmyshow.com",
    "bms": "https://in.bookmyshow.com",
    "pvr": "https://www.pvrcinemas.com",
    "inox": "https://www.inoxmovies.com",
}


class MovieBookingAgent:
    def __init__(self, browser: BrowserController, whatsapp_sender=None):
        self.browser = browser
        self.whatsapp_sender = whatsapp_sender  # Callback to send user confirmation request
        self._user_confirmed = False

    def book_ticket(self, movie: str, date: str = None, show_time: str = None,
                    city: str = None, site: str = "bookmyshow") -> dict:
        """
        Book a movie ticket through BookMyShow.
        IMPORTANT: Always pauses before payment and asks user to confirm.
        """
        try:
            base_url = BOOKING_SITES.get(site.lower(), BOOKING_SITES["bookmyshow"])
            self.browser.goto(base_url)
            time.sleep(3)

            # Step 1: Search for movie
            print(f"[MovieBooking] Searching: {movie}")
            search_result = self._search_movie(movie)
            if not search_result:
                return {"status": "error", "message": f"Could not find '{movie}' on {site}"}

            time.sleep(2)

            # Step 2: Select date (if provided, try to find it)
            if date:
                self._select_date(date)
                time.sleep(1)

            # Step 3: Select show time
            if show_time:
                found = self._select_showtime(show_time)
                if not found:
                    return {
                        "status": "partial",
                        "message": f"⚠️ Movie found but could not auto-select showtime '{show_time}'. Browser is open — please complete booking manually."
                    }

            time.sleep(2)

            # Step 4: Select seats (auto-pick available)
            seats_selected = self._select_seats()
            if not seats_selected:
                return {
                    "status": "partial",
                    "message": "⚠️ Showtime opened — please select seats manually in the browser."
                }

            # Take screenshot before payment
            screenshot = self.browser.screenshot("booking_preview.png")

            # Step 5: PAUSE FOR USER CONFIRMATION before payment
            confirmation_message = (
                f"🎬 *Movie Booking Ready*\n\n"
                f"Film: {movie}\n"
                f"Date: {date or 'Selected'}\n"
                f"Time: {show_time or 'Selected'}\n\n"
                f"Seats selected. Ready to proceed to payment.\n"
                f"Reply *YES* to confirm payment, or *NO* to cancel."
            )

            if self.whatsapp_sender:
                self.whatsapp_sender(confirmation_message)
                print("[MovieBooking] ⏸️ Waiting for user payment confirmation...")

                # Wait up to 5 minutes for user confirmation
                waited = 0
                while waited < 300:
                    time.sleep(5)
                    waited += 5
                    if self._user_confirmed:
                        break
                    # Check WhatsApp for response (simplified — crew_manager handles this)

                if not self._user_confirmed:
                    return {
                        "status": "paused",
                        "message": "⏸️ Booking paused — waiting for your confirmation. Reply YES to proceed with payment.",
                        "screenshot": screenshot
                    }
            else:
                print("[MovieBooking] No WhatsApp sender available — opening browser for manual payment.")
                return {
                    "status": "paused",
                    "message": f"🎬 Movie found! Browser is open at the payment page. Please complete payment manually.\n{confirmation_message}",
                    "screenshot": screenshot
                }

            # Step 6: Proceed to payment (only if confirmed)
            self._proceed_to_payment()
            time.sleep(3)
            final_screenshot = self.browser.screenshot("booking_complete.png")

            return {
                "status": "success",
                "message": f"✅ Booking initiated for {movie}! Check browser to complete payment.",
                "screenshot": final_screenshot,
                "data": confirmation_message
            }

        except Exception as e:
            return {"status": "error", "message": f"Movie booking failed: {e}"}

    def confirm_payment(self):
        """Called when user sends YES confirmation."""
        self._user_confirmed = True

    def _search_movie(self, movie: str) -> bool:
        """Search for a movie on BookMyShow."""
        search_selectors = [
            "input[placeholder*='Search']",
            "input[class*='search']",
            "#globalSearch",
            "[data-testid='search-input']"
        ]
        for sel in search_selectors:
            try:
                self.browser.page.wait_for_selector(sel, timeout=3000)
                self.browser.page.click(sel)
                self.browser.page.type(sel, movie, delay=80)
                time.sleep(2)
                # Click first movie result
                self.browser.page.locator("[class*='search-result']:first-child, [data-testid='movie-card']:first-child").first.click()
                return True
            except Exception:
                continue
        return False

    def _select_date(self, date: str):
        """Try to find and click the matching date."""
        try:
            # Look for date buttons/tabs with the specified date text
            date_variants = [date, date.lower(), date.capitalize()]
            for d in date_variants:
                try:
                    self.browser.page.locator(f"[class*='date']:has-text('{d}')").first.click()
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def _select_showtime(self, show_time: str) -> bool:
        """Find and click a showtime button."""
        try:
            time_variants = [show_time, show_time.upper(), show_time.lower()]
            for t in time_variants:
                try:
                    self.browser.page.locator(f"[class*='show-time']:has-text('{t}'), button:has-text('{t}')").first.click()
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def _select_seats(self) -> bool:
        """Auto-select available seats."""
        try:
            # Click first available seats
            available = self.browser.page.locator("[class*='available']:not([class*='unavailable'])")
            count = available.count()
            if count >= 2:
                available.nth(0).click()
                time.sleep(0.3)
                available.nth(1).click()
                time.sleep(0.3)
                # Confirm seat selection
                self.browser.page.locator("button:has-text('Book'), button:has-text('Proceed')").first.click()
                return True
        except Exception:
            pass
        return False

    def _proceed_to_payment(self):
        """Click Proceed to Payment button."""
        try:
            self.browser.page.locator("button:has-text('Proceed to Pay'), button:has-text('Pay Now')").first.click()
        except Exception:
            pass
