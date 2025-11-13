import time
import getpass
from typing import List, Dict, Optional

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains



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
        - Go (or redirect) to /login.
        - Wait for the real React form to fully load.
        - Fill email/password (and re-fill if React wipes them).
        - Submit via ENTER on password.
        - Wait until we leave /login.
        - Optionally navigate to redirect_to or product_url.
        """
        email = self.email
        password = self.password

        if not email or not password:
            raise RuntimeError("Email or password is empty.")

        print("[login_kream] current url:", self.driver.current_url)

        # 1) Try clicking '로그인' link if present (usually on product/main pages)
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
        except Exception:
            print("[login_kream] No top 로그인 link found (maybe already on /login).")

        # 2) Ensure we are on the login page
        if "kream.co.kr/login" not in self.driver.current_url:
            print("[login_kream] Forcing navigation to /login")
            self.driver.get("https://kream.co.kr/login")

        print("[login_kream] Now at:", self.driver.current_url)

        # *** IMPORTANT: give React time to fully render the real form ***
        time.sleep(2.5)

        # 3) Locate email & password inputs (using the HTML you gave)
        email_input = self.wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//input[@type='email' and contains(@placeholder, 'kream@kream.co.kr')]",
                )
            )
        )
        password_input = self.driver.find_element(By.XPATH, "//input[@type='password']")

        # 4) Fill email and password
        print("[login_kream] Filling in email and password...")
        email_input.clear()
        email_input.send_keys(email)
        password_input.clear()
        password_input.send_keys(password)

        # 4.1) Wait a bit to see if React wipes the values, and re-fill once if needed
        time.sleep(1.0)
        current_email_val = email_input.get_attribute("value")
        current_pw_val = password_input.get_attribute("value")
        print(f"[login_kream] After typing, email value: {current_email_val!r}")

        if current_email_val != email or not current_pw_val:
            print("[login_kream] Detected cleared/changed inputs, re-filling once...")
            # Re-find inputs (in case DOM re-rendered)
            email_input = self.driver.find_element(
                By.XPATH,
                "//input[@type='email' and contains(@placeholder, 'kream@kream.co.kr')]",
            )
            password_input = self.driver.find_element(
                By.XPATH, "//input[@type='password']"
            )
            email_input.clear()
            email_input.send_keys(email)
            password_input.clear()
            password_input.send_keys(password)
            time.sleep(0.8)

        # 5) Submit the form via ENTER on the password field
        print("[login_kream] Submitting login form via ENTER on password...")
        password_input.send_keys(Keys.RETURN)

        # 6) Wait until we leave /login (successful login or some redirect)
        logged_in = False
        try:
            self.wait.until(lambda d: "kream.co.kr/login" not in d.current_url)
            logged_in = True
            print("[login_kream] Logged in, new url:", self.driver.current_url)
        except TimeoutException:
            print(
                "[login_kream] Still on /login after submit. Maybe wrong credentials or extra auth."
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
            print("[_click_details_button] Looking for '자세히' text element...")
            # First, locate the <p> element with the text '자세히'
            details_text = self.wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//p[contains(@class, 'text-lookup') and contains(normalize-space(.), '자세히')]",
                    )
                )
            )

            # Scroll into view
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", details_text
            )
            time.sleep(0.5)

            # Try to find a clickable ancestor: button, a, or role='button'
            clickable = None
            try:
                clickable = details_text.find_element(
                    By.XPATH,
                    "./ancestor::*[self::button or self::a or @role='button'][1]",
                )
                print("[_click_details_button] Found clickable ancestor element.")
            except Exception:
                print(
                    "[_click_details_button] No clickable ancestor found, "
                    "using the <p> element itself."
                )
                clickable = details_text

            # Try an ActionChains click first (more human-like)
            try:
                print("[_click_details_button] Trying ActionChains click...")
                actions = ActionChains(self.driver)
                actions.move_to_element(clickable).click().perform()
            except Exception as e:
                print(f"[_click_details_button] ActionChains click failed: {e}")
                print("[_click_details_button] Falling back to JS click...")
                self.driver.execute_script("arguments[0].click();", clickable)

            time.sleep(1.5)
            print("[_click_details_button] Click on '자세히' attempted.")

        except TimeoutException:
            raise RuntimeError("Could not find the '자세히' button.")


    # ---------- SCROLLING & SCRAPING ----------

    def scrape_trade_history(self) -> List[Dict[str, str]]:
        """
        Scrape trade rows (size / price / date) from the market_price_table.

        Uses the structure:
          <div class="market_price_table">
            <div class="price_body">
              <div class="body_list ...">
                <div class="list_txt"><span>SIZE</span></div>
                <div class="list_txt"><span>PRICE</span></div>
                <div class="list_txt"><span>DATE/TIME</span></div>
        """
        # Give the UI a bit of time after clicking '자세히'
        time.sleep(1.5)

        # 1) Find the main container for the trade list
        container = self.wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.market_price_table")
            )
        )

        # 2) Each row is a body_list
        rows = container.find_elements(By.CSS_SELECTOR, "div.price_body div.body_list")

        records: List[Dict[str, str]] = []

        for row in rows:
            try:
                # Each row has three list_txt blocks with <span>text</span>
                cells = row.find_elements(By.CSS_SELECTOR, "div.list_txt span")
                if len(cells) < 3:
                    continue

                size = cells[0].text.strip()
                price = cells[1].text.strip()
                date = cells[2].text.strip()

                if not size and not price and not date:
                    continue

                records.append(
                    {
                        "size": size,
                        "price": price,
                        "date": date,
                    }
                )
            except Exception:
                # Skip weird/incomplete rows
                continue

        print(f"[scrape_trade_history] Collected {len(records)} rows.")
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
