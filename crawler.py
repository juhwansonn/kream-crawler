import os
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


        def login_kream(self) -> None:
            """
            Ensure we're logged into KREAM.

            Flow:
            - If there's a '로그인' link on the current page, click it.
            - Land on https://kream.co.kr/login
            - Fill email & password (from env vars) and submit.
            - Wait until we are no longer on /login.
            """
            email = self.email
            password = self.password

            if not email or not password:
                raise RuntimeError("Email or password is empty.")
            # 1) If we're on a page with a '로그인' top link, click it.

            try:
                login_link = self.driver.find_element(
                    By.XPATH, "//a[contains(@class, 'top_link') and contains(normalize-space(.), '로그인')]"
                )
                # If found, click it to go to /login
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", login_link
                )
                time.sleep(0.3)
                login_link.click()
            except Exception:
                # No login link found: maybe already on login page or already logged in.
                pass

            # 2) If we're not on /login yet, go there explicitly
            if "kream.co.kr/login" not in self.driver.current_url:
                self.driver.get("https://kream.co.kr/login")

            # 3) If we still somehow got redirected away from /login, assume logged in
            if "kream.co.kr/login" not in self.driver.current_url:
                return

            # 4) Now fill in the login form
            # Email input: <input type="email" class="input_txt text_fill" ...>
            email_input = self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[type='email'].input_txt.text_fill")
                )
            )

            # Password input: <input type="password" class="input_txt text_fill" ...>
            password_input = self.driver.find_element(
                By.CSS_SELECTOR, "input[type='password'].input_txt.text_fill"
            )

            email_input.clear()
            email_input.send_keys(email)
            password_input.clear()
            password_input.send_keys(password)

            # 5) Find 로그인 button and wait until it's enabled (no disabled attr)
            login_button_locator = (
                By.XPATH,
                "//button[contains(normalize-space(.), '로그인')]",
            )

            self.wait.until(
                lambda d: not d.find_element(*login_button_locator).get_attribute("disabled")
            )

            login_button = self.driver.find_element(*login_button_locator)

            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", login_button
            )
            time.sleep(0.3)
            login_button.click()

            # 6) Wait until we leave /login (successful login or some redirect)
            try:
                self.wait.until(lambda d: "kream.co.kr/login" not in d.current_url)
            except TimeoutException:
                raise RuntimeError(
                    "Still on login page after submitting. Check credentials or extra auth."
                )





    # ---------- HIGH-LEVEL FLOW ----------

    def open_product_and_modal(self) -> None:
        """Open product page, log in (if needed), and open trade history modal."""
        self.driver.get(self.product_url)

        # If you want to login before going to product page, move login_kream() above.
        self.login_kream(email="", password="")

        # Wait for page to fully load something meaningful (like the title or price)
        time.sleep(2)

        # Click "자세히" (the element you showed: <p class="text-lookup ...>자세히</p>)
        self._click_details_button()

        # Wait until the modal is visible – we look for some text that should appear
        # in the trade history area; adjust the text if KREAM uses something else.
        try:
            self.wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//*[contains(text(), '체결 거래') or contains(text(), '거래 내역')]")
                )
            )
        except TimeoutException:
            print("⚠️ Could not confirm that the trade history modal is open.")
            # Not fatal; we continue and try to scrape anyway.

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
