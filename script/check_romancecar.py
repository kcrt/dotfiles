#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# to install driver, run:
#   brew install chromedriver (for Mac)
#   sudo apt install python3-selenium (for Ubuntu)

# requires: selenium

USER_ID = os.environ.get("ODAKYU_USER_ID")
USER_PASS = os.environ.get("ODAKYU_USER_PASS")


def main():

    result_str = "来週のロマンスカー運行状況\n"

    if USER_ID is None or USER_PASS is None:
        raise Exception("Please set ODAKYU_USER_ID and ODAKYU_USER_PASS.")

    # Run every monday

    options = webdriver.ChromeOptions()
    if not os.environ.get("DEBUG"):
        options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    driver.get("https://www.web-odakyu.com/wsr/login")
    time.sleep(5)

    assert "ロマンスカー＠クラブ" in driver.title
    assert "ログイン" in driver.title
    driver.find_element(by=By.NAME, value="memberNo").send_keys(USER_ID)
    driver.find_element(by=By.NAME, value="password").send_keys(USER_PASS)
    time.sleep(1)
    driver.find_element(
        by=By.XPATH, value="//form/div[4]/button").submit()
    time.sleep(1)

    # assert driver.current_url == "https://www.web-odakyu.com/wsr/"
    # driver.find_element(
    #     by=By.XPATH, value="//form[@id='logmenu_btn']/div[1]/a").click()
    # time.sleep(5)

    next_monday = datetime.date.today() + datetime.timedelta(days=7 -
                                                             datetime.date.today().weekday())

    for i in range(5):
        target_date = next_monday + datetime.timedelta(days=i)

        driver.get("https://www.web-odakyu.com/wsr/vacantSeatInquiry/")
        assert "空席照会／予約／購入" in driver.title
        target_date_str = target_date.strftime("%Y-%m-%d")
        driver.execute_script(
            "document.getElementsByName('req_date')[0].value = '" + target_date_str + "'")
        driver.execute_script(
            "document.getElementsByName('req_time')[0].value = '08:30'")
        driver.execute_script(
            "document.getElementById('s_eki_cod').value = '0030'")
        driver.execute_script(
            "document.getElementById('e_eki_cod').value = '2832'")
        time.sleep(5)
        cmdSearch = driver.find_element(
            by=By.XPATH, value="//form[@id='vacantSeatInquiryForm']/div[6]/div[2]/button")
        driver.execute_script("arguments[0].scrollIntoView(false);", cmdSearch)
        time.sleep(3)
        cmdSearch.click()
        time.sleep(3)

        assert "空席照会／予約／購入 空席状況" in driver.title
        dateinfo_str = target_date.strftime("%-m月%-d日(%a)") + ": "
        body_str: str = driver.find_element(by=By.TAG_NAME, value="body").text
        if "メトロモーニングウェイ４２号 (MSE10)" in body_str:
            result_str += dateinfo_str + "10 cars.\n"
        elif "メトロモーニングウェイ４２号 (MSE6)" in body_str:
            result_str += dateinfo_str + "⚠︎ 6 cars.\n"
            # add_to_calendar(target_date_str, "[6] 🚃")
        else:
            # ない: 祝日など
            result_str += dateinfo_str + "⚠︎ Unknown.\n"

    driver.find_element(
        by=By.XPATH, value='//*[@id="logout"]/button').click()  # logout
    time.sleep(5)

    driver.close()

    print(result_str)


if __name__ == '__main__':
    main()
