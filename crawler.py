import time
import getpass
from typing import List, Dict, Optional

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


# =============================
# Configuration
# =============================

DEFAULT_PRODUCT_URL = "https://kream.co.kr/products/83900"
DEFAULT_OUTPUT_FILE = "kream_83900.xlsx"


# =============================
# Core crawler
# =============================

class KreamCrawler:
    def __init__(self, driver: webdriver.Chrome, product_url: str, email: str, password: str):
        self.driver = driver
        self.product_url = product_url
        self.email = email
        self.password = password
        self.wait = WebDriverWait(self.driver, 15)

    @staticmethod
    def _normalize_url(url: Optional[str]) -> str:
        """
        Strip query parameters and trailing slashes to make URL comparisons
        more forgiving when checking navigation state.
        """
        if not url:
            return ""
        return url.split("?", 1)[0].rstrip("/")

    def _navigate_if_needed(self, target_url: Optional[str]) -> None:
        """
        Navigate to `target_url` only when we are not already there. This avoids
        redundant GET calls that can invalidate temporary tokens during login.
        """
        if not target_url:
            return

        desired = self._normalize_url(target_url)
        current = self._normalize_url(self.driver.current_url)
        if desired and desired == current:
            return

        print(f"[navigation] Navigating to {target_url}")
        self.driver.get(target_url)
        try:
            self.wait.until(
                lambda d: self._normalize_url(d.current_url) == desired
            )
        except TimeoutException:
            print(
                f"[navigation] Timed out waiting for {target_url}. "
                f"Current url: {self.driver.current_url}"
            )


    def login_kream(self, redirect_to: Optional[str] = None) -> None:
        """
        Ensure we're logged into KREAM using the email/password
        stored on this KreamCrawler instance.

        Flow:
        - If there's a '로그인' link on the current page, click it.
        - Otherwise go directly to /login.
        - Fill email/password.
        - Click 로그인 and wait until we leave /login.
        """
        email = self.email
        password = self.password

        if not email or not password:
            raise RuntimeError("Email or password is empty.")

        print("[login_kream] current url:", self.driver.current_url)

        # 1) If there is a '로그인' link (top right), click it to go to /login
        try:
            login_link = self.driver.find_element(
                By.XPATH,
                "//a[contains(@class, 'top_link') and contains(normalize-space(.), '로그인')]",
            )
            print("[login_kream] Found top 로그인 link, clicking it...")
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", login_link
            )
            time.sleep(0.3)
            login_link.click()
            time.sleep(1.0)
        except Exception:
            print("[login_kream] No top 로그인 link found (maybe already on /login).")

        # 2) Make sure we're on the login page
        if "kream.co.kr/login" not in self.driver.current_url:
            print("[login_kream] Forcing navigation to /login")
            self.driver.get("https://kream.co.kr/login")
            time.sleep(1.0)

        print("[login_kream] Now at:", self.driver.current_url)

        # 3) Locate email & password inputs (using the HTML you gave)
        email_input = self.wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//input[@type='email' and contains(@placeholder, 'kream@kream.co.kr')]",
                )
            )
        )
        password_input = self.driver.find_element(
            By.XPATH, "//input[@type='password']"
        )

        print("[login_kream] Filling in email and password...")
        email_input.clear()
        email_input.send_keys(email)
        password_input.clear()
        password_input.send_keys(password)

        # 4) Find the 로그인 button
        login_button = self.driver.find_element(
            By.XPATH, "//button[contains(normalize-space(.), '로그인')]"
        )
        print(
            "[login_kream] login button disabled attribute BEFORE click:",
            login_button.get_attribute("disabled"),
        )

        # 5) Click the 로그인 button (JS click to be extra sure)
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", login_button
        )
        time.sleep(0.3)
        print("[login_kream] Clicking 로그인 button...")
        self.driver.execute_script("arguments[0].click();", login_button)

        # 6) Wait until we leave /login (successful login or some redirect)
        logged_in = False
        try:
            self.wait.until(lambda d: "kream.co.kr/login" not in d.current_url)
            logged_in = True
            print("[login_kream] Logged in, new url:", self.driver.current_url)
        except TimeoutException:
            print(
                "[login_kream] Still on /login after clicking. Maybe wrong credentials or extra auth."
            )
            logged_in = "kream.co.kr/login" not in self.driver.current_url

        # 7) Optionally redirect straight to the desired page (usually the product)
        target_after_login = redirect_to or self.product_url
        if target_after_login and logged_in:
            print(f"[login_kream] Redirecting to target page: {target_after_login}")
            self._navigate_if_needed(target_after_login)
            print("[login_kream] Final url after redirect:", self.driver.current_url)





    # ---------- HIGH-LEVEL FLOW ----------

    def open_product_and_modal(self) -> None:
        """
        1) Log in (via login_kream)
        2) Go to the product page
        3) Click '자세히' to open the trade history modal
        """
        # Step 1: login
        print("[open_product_and_modal] Step 1: login")
        self.login_kream(redirect_to=self.product_url)
        print("[open_product_and_modal] after login, url:", self.driver.current_url)

        # Step 2: ensure product page is open (safety net)
        print("[open_product_and_modal] Step 2: ensure product page is open")
        self._navigate_if_needed(self.product_url)
        time.sleep(2.0)
        print("[open_product_and_modal] now at:", self.driver.current_url)

        # Step 3: click "자세히" on the product page
        print("[open_product_and_modal] Step 3: click '자세히'")
        self._click_details_button()

        # Step 4: wait for trade history modal to appear
        try:
            self.wait.until(
                EC.visibility_of_element_located(
                    (
                        By.XPATH,
                        "//*[contains(text(), '체결 거래') or "
                        "contains(text(), '거래 및 입찰 내역') or "
                        "contains(text(), '거래 내역')]",
                    )
                )
            )
            print("[open_product_and_modal] Trade history modal detected.")
        except TimeoutException:
            print("⚠️ Could not confirm that the trade history modal is open.")



    def _click_details_button(self) -> None:
        """Click the '자세히' button on the right side."""
        try:
            details_element = self.wait.until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        # Your snippet: <p class="text-lookup ...>자세히</p>
                        # We search for a <p> with class containing text-lookup and inner text '자세히'
                        "//p[contains(@class, 'text-lookup') and contains(normalize-space(.), '자세히')]"
                    )
                )
            )
            # Scroll it into view just in case
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", details_element)
            time.sleep(0.5)
            details_element.click()
        except TimeoutException:
            raise RuntimeError("Could not find or click the '자세히' button.")

    # ---------- SCROLLING & SCRAPING ----------

    def scrape_trade_history(self) -> List[Dict[str, str]]:
        """
        Scrape ALL trade rows (size / price / date) from the modal.

        This version:
        - Scrolls the window repeatedly until no more rows are added.
        - Assumes there is a <table> in the modal; we collect <tr> rows.
        - For each row, we take first 3 non-empty cells as size / price / date.

        If KREAM uses a DIV-based layout instead of <table>, you’ll only need to
        change the selectors inside this method.
        """
        # Give modal some time to fully render
        time.sleep(1.5)

        # Try to locate the table that holds the trade history.
        # You may have to tweak this XPATH based on actual HTML.
        table = self.wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    # "any table inside the currently visible modal"
                    "//div[contains(@class, 'layer')]//table | //div[contains(@role, 'dialog')]//table"
                )
            )
        )

        records: List[Dict[str, str]] = []
        last_count = -1

        while True:
            # Get current rows
            rows = table.find_elements(By.XPATH, ".//tbody/tr | .//tr")
            current_count = len(rows)

            # If row count didn't change after scrolling -> done
            if current_count == last_count:
                break

            last_count = current_count

            # Scroll down to load more rows (simple version: scroll window)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.0)

        # Final rows after all scrolling
        rows = table.find_elements(By.XPATH, ".//tbody/tr | .//tr")

        for row in rows:
            try:
                cells = row.find_elements(By.XPATH, ".//td | .//th | .//div")
                texts = [c.text.strip() for c in cells if c.text.strip()]

                if len(texts) < 3:
                    continue

                size = texts[0]
                price = texts[1]
                date = texts[2]

                records.append(
                    {
                        "size": size,
                        "price": price,
                        "date": date,
                    }
                )
            except Exception:
                # Skip weird rows like headers, etc.
                continue

        return records

    # ---------- SAVE TO EXCEL ----------

    @staticmethod
    def save_to_excel(records: List[Dict[str, str]], filename: str) -> None:
        if not records:
            print("⚠️ No records to save.")
            return
        df = pd.DataFrame(records)
        df.to_excel(filename, index=False)
        print(f"✅ Saved {len(df)} rows to {filename}")


# =============================
# Convenience function
# =============================

def crawl_product(
    product_url: str,
    output_file: str,
    email: str,
    password: str,
    driver: Optional[webdriver.Chrome] = None,
) -> None:

    """
    High-level helper for other scripts (e.g., main.py).
    Creates a driver if one isn't given, crawls, and saves to Excel.
    """
    own_driver = False
    if driver is None:
        own_driver = True
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        driver = webdriver.Chrome(options=options)

    try:
        crawler = KreamCrawler(driver, product_url, email, password)
        crawler.open_product_and_modal()
        records = crawler.scrape_trade_history()
        crawler.save_to_excel(records, output_file)
    finally:
        if own_driver:
            driver.quit()



# =============================
# CLI entrypoint
# =============================

if __name__ == "__main__":
    import getpass

    product_url = DEFAULT_PRODUCT_URL
    output_file = DEFAULT_OUTPUT_FILE

    print("KREAM login required.")
    email = input("KREAM email: ").strip()
    password = getpass.getpass("KREAM password: ")

    crawl_product(
        product_url=product_url,
        output_file=output_file,
        email=email,
        password=password,
    )
