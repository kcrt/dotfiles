#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import datetime

# to install driver, run:
#   brew install chromedriver (for Mac)
#   sudo apt install python3-selenium (for Ubuntu)


USER_ID = os.environ.get("ODAKYU_USER_ID")
USER_PASS = os.environ.get("ODAKYU_USER_PASS")


def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)
    driver.get("https://www.web-odakyu.com/")
    time.sleep(5)

    assert driver.title == "ロマンスカー＠club　PC"
    driver.find_element(by=By.NAME, value="account").send_keys(USER_ID)
    driver.find_element(by=By.NAME, value="password").send_keys(USER_PASS)
    driver.find_element(
        by=By.XPATH, value="//input[@id='ImageM4']/ancestor::form").submit()
    time.sleep(5)

    assert driver.title == "会員メニュー(020)"
    driver.find_element(
        by=By.XPATH, value="//*[@id='logmenu_btn']/div[1]/a").click()
    time.sleep(5)

    assert driver.title == "空席照会／座席予約(100)"
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y%m%d")
    driver.find_element(by=By.ID, value="on_month").send_keys(
        tomorrow.strftime("%m"))
    driver.find_element(by=By.ID, value="on_day").send_keys(
        tomorrow.strftime("%d"))
    driver.find_element(by=By.NAME, value="on_hour").send_keys("08")
    driver.find_element(by=By.NAME, value="on_minute").send_keys("30")
    driver.find_element(by=By.ID, value="syuppatu").send_keys("町田")
    driver.find_element(by=By.ID, value="toutyaku").send_keys("大手町")
    driver.find_element(by=By.NAME, value="Image44").click()
    time.sleep(10)

    assert driver.title == "空席状況(101)"
    body_str: str = driver.find_element(by=By.TAG_NAME, value="body").text
    if "メトロモーニングウェイ４２号(MSE10)" in body_str:
        # its's ok. 10 cars.
        os.system("~/dotfiles/script/notify-slack.sh \"明日のロマンスカーは10両編成です。\"")
    elif "メトロモーニングウェイ４２号(MSE6)" in body_str:
        # Reserve now!
        os.system("~/dotfiles/script/notify-slack.sh \"⚠︎明日のロマンスカーは6両編成です。\"")
    else:
        # Unknown error.
        os.system("~/dotfiles/script/notify-slack.sh \"Unknown error.\"")

    driver.find_element(
        by=By.XPATH, value='//*[@id="name"]/tbody/tr/td[2]/div/a/img').click()  # logout
    time.sleep(5)

    driver.close()


if __name__ == '__main__':
    main()
