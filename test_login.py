# test_login.py
from selenium import webdriver
from crawler import KreamCrawler, DEFAULT_PRODUCT_URL
import getpass
import time


def main():
    print("KREAM login test")
    email = input("KREAM email: ").strip()
    password = getpass.getpass("KREAM password: ")

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)

    try:
        # 1) Go to product page first so the top '로그인' link exists
        driver.get(DEFAULT_PRODUCT_URL)
        time.sleep(1.5)

        # 2) Create crawler and run ONLY login
        crawler = KreamCrawler(driver, DEFAULT_PRODUCT_URL, email, password)
        crawler.login_kream()

        print("✅ login_kream finished. Check the browser window to confirm login.")
        input("Press Enter to close the browser...")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
