#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import sys

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

    if USER_ID is None or USER_LOGIN_PASS is None or USER_TRANSACTION_PASS is None:
        raise Exception(
            "Please set SBI_ID, SBI_LOGIN_PASS, SBI_TRANSACTION_PASS as environment variables.")

    if is_venv():
        print("Currently running inside a virtual environment.")
    else:
        print("Not running inside a virtual environment")

    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    driver.get("https://www.sbisec.co.jp/ETGate")
    time.sleep(3)

    assert "SBI証券" in driver.title
    driver.find_element(by=By.NAME, value="user_id").send_keys(USER_ID)
    driver.find_element(
        by=By.NAME, value="user_password").send_keys(USER_LOGIN_PASS)
    time.sleep(5)
    driver.find_element(by=By.NAME, value="ACT_login").click()
    time.sleep(3)

    print("--- IPO申込 ---")
    while True:
        driver.get("https://site2.sbisec.co.jp/ETGate/")
        time.sleep(1)

        # find h3 tag whose contents is "IPO・PO".
        ipo_tag = [x for x in driver.find_elements(
            by=By.TAG_NAME, value="h5") if x.text == "IPO・PO"][0]
        parent_div = ipo_tag.find_element(by=By.XPATH, value="../../..")
        linkIPO = [x for x in parent_div.find_elements(
            by=By.TAG_NAME, value="a") if "一覧" in x.text][0]
        driver.execute_script("arguments[0].scrollIntoView(false);", linkIPO)
        linkIPO.click()
        time.sleep(5)

        assert driver.find_element(
            by=By.CSS_SELECTOR, value="h1.ttl").text == "新規上場株式 公募増資・売出ブックビルディング情報"

        t = [x for x in driver.find_elements(by=By.TAG_NAME, value="img") if x.get_attribute(
            "alt") == "新規上場株式ブックビルディング / 購入意思表示"]

        if len(t) == 0:
            break
        driver.execute_script("arguments[0].scrollIntoView(false);", t[0])
        t[0].click()
        time.sleep(2)

        # print(driver.find_element(by=By.TAG_NAME, value="h2").text)
        assert driver.find_element(
            by=By.TAG_NAME, value="h2").text == "新規上場株式ブックビルディング / 購入意思表示"

        t = [x for x in driver.find_elements(by=By.TAG_NAME, value="img") if x.get_attribute(
            "alt") == "申込"]

        if len(t) == 0:
            break
        driver.execute_script("arguments[0].scrollIntoView(false);", t[0])
        t[0].click()
        time.sleep(2)

        corp_name = [x for x in driver.find_elements(
            by=By.TAG_NAME, value="td") if "mbody" in x.get_attribute("class")][0].text
        print(corp_name)

        time.sleep(3)
        driver.find_element(
            by=By.NAME, value="suryo").send_keys("200")
        [x for x in driver.find_elements(
            by=By.TAG_NAME, value="label") if "ストライクプライス" in x.text][0].click()
        [x for x in driver.find_elements(
            by=By.TAG_NAME, value="label") if "使用する" in x.text][0].click()
        driver.find_element(
            by=By.NAME, value="usePoint").send_keys("3")
        driver.find_element(
            by=By.NAME, value="tr_pass").send_keys(USER_TRANSACTION_PASS)
        time.sleep(1)
        driver.find_element(
            by=By.NAME, value="order_kakunin").click()
        time.sleep(3)

        assert "新規上場株式ブックビルディング申込確認" in driver.find_element(
            by=By.TAG_NAME, value="body").text

        driver.find_element(by=By.NAME, value="order_btn").click()
        time.sleep(5)

    driver.close()


if __name__ == '__main__':
    main()
