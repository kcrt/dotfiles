#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import sys
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By

# to install driver, run:
#   brew install chromedriver (for Mac)
#   sudo apt install python3-selenium (for Ubuntu)

# requires: selenium

USER_ID = os.environ.get("SBI_ID")
USER_LOGIN_PASS = os.environ.get("SBI_LOGIN_PASS")
USER_TRANSACTION_PASS = os.environ.get("SBI_TRANSACTION_PASS")


def is_venv():
    return (hasattr(sys, 'real_prefix') or
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='SBI IPO application automation')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose debug output')
    parser.add_argument('--gui', action='store_true', help='Run with GUI (non-headless mode)')
    args = parser.parse_args()
    
    verbose = args.verbose
    
    if verbose:
        print("Verbose mode enabled")
    
    if USER_ID is None or USER_LOGIN_PASS is None or USER_TRANSACTION_PASS is None:
        raise Exception(
            "Please set SBI_ID, SBI_LOGIN_PASS, SBI_TRANSACTION_PASS as environment variables.")

    if is_venv():
        print("Currently running inside a virtual environment.")
    else:
        print("Not running inside a virtual environment")
        
    if verbose:
        print("Setting up Chrome driver...")

    options = webdriver.ChromeOptions()
    if not args.gui:
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
    if verbose:
        print("Chrome options configured")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    if verbose:
        print("Opening SBI Securities website...")
    driver.get("https://www.sbisec.co.jp/ETGate")
    time.sleep(3)

    assert "SBI証券" in driver.title
    if verbose:
        print(f"Page title: {driver.title}")
        print("Logging in...")
    driver.find_element(by=By.NAME, value="user_id").send_keys(USER_ID)
    driver.find_element(
        by=By.NAME, value="user_password").send_keys(USER_LOGIN_PASS)
    time.sleep(5)
    driver.find_element(by=By.NAME, value="ACT_login").click()
    time.sleep(3)
    if verbose:
        print("Login successful")

    print("--- IPO申込 ---")
    while True:
        if verbose:
            print("Navigating to domestic stock page...")
        driver.get("https://site2.sbisec.co.jp/ETGate/")
        time.sleep(1)
        driver.get("https://site0.sbisec.co.jp/marble/domestic/top.do?")    # 国内株式
        time.sleep(1)

        # find h3 tag whose contents is "IPO・PO".
        # ipo_tag = [x for x in driver.find_elements(
        #     by=By.TAG_NAME, value="h5") if x.text == "IPO・PO"][0]
        # parent_div = ipo_tag.find_element(by=By.XPATH, value="../../..")
        # linkIPO = [x for x in parent_div.find_elements(
        #     by=By.TAG_NAME, value="a") if "一覧" in x.text][0]
        # driver.execute_script("arguments[0].scrollIntoView(false);", linkIPO)
        # linkIPO.click()
        # time.sleep(5)

        # find a tag with text "IPO・PO" under div.navi2M
        if verbose:
            print("Looking for IPO・PO link...")
        ipo_tag = [x for x in driver.find_elements(
            by=By.CSS_SELECTOR, value="div.navi2M a") if x.text == "IPO・PO"][0]
        ipo_tag.click()
        time.sleep(5)
        if verbose:
            print("Navigated to IPO page")

        assert driver.find_element(
            by=By.CSS_SELECTOR, value="h1.ttl").text == "新規上場株式 公募増資・売出ブックビルディング情報"
        if verbose:
            print("Confirmed page title")

        if verbose:
            print("Looking for bookbuilding button...")
        # The button changed from img to span
        t = [x for x in driver.find_elements(by=By.TAG_NAME, value="span") if "新規上場株式ブックビルディング" in x.text and "購入意思表示" in x.text]

        if len(t) == 0:
            if verbose:
                print("No bookbuilding button found, exiting loop")
            break
        driver.execute_script("arguments[0].scrollIntoView(false);", t[0])
        t[0].click()
        time.sleep(2)
        if verbose:
            print("Clicked on bookbuilding button")

        # print(driver.find_element(by=By.TAG_NAME, value="h2").text)
        assert driver.find_element(
            by=By.TAG_NAME, value="h2").text == "新規上場株式ブックビルディング / 購入意思表示"
        if verbose:
            print("Confirmed bookbuilding page")

        if verbose:
            print("Looking for application button...")
        t = [x for x in driver.find_elements(by=By.TAG_NAME, value="img") if x.get_attribute(
            "alt") == "申込"]

        if len(t) == 0:
            if verbose:
                print("No application button found, exiting loop")
            break
        driver.execute_script("arguments[0].scrollIntoView(false);", t[0])
        t[0].click()
        time.sleep(2)
        if verbose:
            print("Clicked on application button")

        # Find the corporation name from the td element with class containing "mbody"
        td_elements = driver.find_elements(by=By.TAG_NAME, value="td")
        corp_name = None
        for td in td_elements:
            class_attr = td.get_attribute("class")
            if class_attr and "mbody" in class_attr:
                corp_name = td.text
                break
        
        if corp_name:
            print(corp_name)
            if verbose:
                print(f"Found corporation: {corp_name}")
        else:
            print("Corporation name not found")
            if verbose:
                print("Could not find td element with 'mbody' class")

        time.sleep(3)
        if verbose:
            print("Filling application form...")
        driver.find_element(
            by=By.NAME, value="suryo").send_keys("200")
        if verbose:
            print("Set quantity to 200")
        [x for x in driver.find_elements(
            by=By.TAG_NAME, value="label") if "ストライクプライス" in x.text][0].click()
        if verbose:
            print("Selected strike price")

        IPO_POINT = 2
        if IPO_POINT == 0:
            [x for x in driver.find_elements(
                by=By.TAG_NAME, value="label") if "使用しない" in x.text][0].click()
            if verbose:
                print("Selected not to use IPO points")
        else:
            [x for x in driver.find_elements(
                by=By.TAG_NAME, value="label") if "使用する" in x.text][0].click()
            driver.find_element(
                by=By.NAME, value="usePoint").send_keys(str(IPO_POINT))    # IPO Points
            if verbose:
                print(f"Set to use {IPO_POINT} IPO points")
        driver.find_element(
            by=By.NAME, value="tr_pass").send_keys(USER_TRANSACTION_PASS)
        if verbose:
            print("Entered transaction password")
        time.sleep(1)
        driver.find_element(
            by=By.NAME, value="order_kakunin").click()
        if verbose:
            print("Clicked confirmation button")
        time.sleep(3)

        assert "新規上場株式ブックビルディング申込確認" in driver.find_element(
            by=By.TAG_NAME, value="body").text
        if verbose:
            print("Confirmed on confirmation page")

        driver.find_element(by=By.NAME, value="order_btn").click()
        if verbose:
            print("Submitted application")
        time.sleep(5)

    if verbose:
        print("All applications completed, closing browser")
    driver.close()


if __name__ == '__main__':
    main()
