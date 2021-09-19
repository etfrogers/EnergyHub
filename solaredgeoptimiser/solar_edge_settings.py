import datetime
import json
import logging
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from importlib_resources import files
import pymsgbox

from solaredgeoptimiser.config import config

COOKIE_FILE_NAME = 'cookies.json'
COOKIE_BASE_PATH = 'solaredgeoptimiser'
COOKIE_FILE_PATH = files(COOKIE_BASE_PATH).joinpath(COOKIE_FILE_NAME)

MONITORING_URL = 'https://monitoring.solaredge.com'

DASHBOARD_URL = f"{MONITORING_URL}/solaredge-web/p/site/{config['solar-edge-site-id']}/#/dashboard"
STORAGE_PROFILE_URL = f'{MONITORING_URL}/solaredge-web/p/home#/account/{config["solar-edge-account-id"]}/storage'

CHROMEDRIVER_PATH = "/Users/user/bin/chromedriver"
logger = logging.getLogger(__name__)


class SolarEdgeAuthenticationError(Exception):
    pass


class LoginCancelledException(Exception):
    pass


class SolarEdgeConnection:
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None

    def __enter__(self):
        self.start_solar_edge_session()
        return self

    def start_solar_edge_session(self):
        logger.debug('Starting browser session with solar edge')
        self.start_chrome()
        self.login_using_cached_cookies()
        logged_in = self.check_login()
        logger.info('Automatic login failed. Trying manual login.')
        while not logged_in:
            try:
                self.manual_login()
                logged_in = self.check_login()
            except LoginCancelledException:
                break
        if not logged_in:
            raise SolarEdgeAuthenticationError()

    def manual_login(self):
        logger.debug('Starting manual login process')
        login_confirmed = pymsgbox.confirm(title='Manual Solar Edge login',
                                           text='Would you like to perform a manual login?',
                                           buttons=['Yes', 'No'],
                                           timeout=30_000)
        # Return value can be 'Yes', 'No', or 'Timeout'
        if login_confirmed != 'Yes':
            logger.debug(f'Manual Login was cancelled (msg box returned "{login_confirmed}"')
            raise LoginCancelledException()

        logger.debug('Showing login page')
        self.go_home()
        login_done = pymsgbox.confirm(title='Manual Solar Edge login',
                                      text='Press OK when logged in, or Cancel to abort.',
                                      buttons=['OK', 'Cancel'])
        logger.debug(f'Confirmation box returned: {login_done}')
        if login_done != 'OK':
            logger.info(f'Manual Login was cancelled (msg box returned "{login_confirmed}"')
            raise LoginCancelledException()
        logger.debug('Manual login confirmed')
        self.save_cookies()

    def save_cookies(self):
        logger.debug('Saving cookies')
        cookies = self.driver.get_cookies()
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = files(COOKIE_BASE_PATH).joinpath(timestamp + COOKIE_FILE_NAME)
        logger.debug(f'Saving to timestamped file: {filename}')
        with open(filename, 'w') as file:
            json.dump(cookies, file)
        logger.debug('Saving to cache file')
        with open(COOKIE_FILE_PATH, 'w') as file:
            json.dump(cookies, file)

    def check_login(self) -> bool:
        self.go_to_dashboard()
        try:
            site_name = WebDriverWait(self.driver, 10).until(
                expected_conditions.presence_of_element_located((By.ID, "se-siteDetailsPanel-name")))
            if not ('Dashboard' in self.driver.title and '4 Dene Road' in site_name.text):
                return False
        except TimeoutException:
            return False
        return True

    def go_to_dashboard(self):
        self.driver.get(DASHBOARD_URL)

    def login_using_cached_cookies(self):
        logger.debug('Reloading cached cookies')
        # visit root site to allow cookie setting (can only be set for current domain)
        self.go_home()
        with open(COOKIE_FILE_PATH, 'r') as file:
            cookies = json.load(file)
        for cookie in cookies:
            self.driver.add_cookie(cookie)

    def go_home(self):
        self.driver.get(MONITORING_URL)

    def start_chrome(self):
        options = Options()
        options.add_argument("--window-size=1920x1080")
        options.add_argument("--verbose")
        self.driver = webdriver.Chrome(options=options, executable_path=CHROMEDRIVER_PATH)

    def go_to_storage_profile(self):
        logger.debug('Loading Storage Profile page')
        self.driver.get(STORAGE_PROFILE_URL)

        profile_link = self.find_element_by_text(config["storage-profile-name"])
        logger.debug(f'Pressing link \"{config["storage-profile-name"]}\"')
        profile_link.click()

    def add_special_day(self, profile):
        add_button = self.find_element_by_text('+ Add Special Day', 'button')
        add_button.click()
        # Need to do one which waits first
        create_button = self.find_element_by_text('Create', 'button')
        name_box = self.driver.find_elements_by_name('name')[-1]
        description_box = self.driver.find_element_by_name('description')
        links = [e.text for e in self.driver.find_elements_by_class_name('se-link')]
        first_seasonal_link = 'Self consumption'
        profiles = links[:links.index(first_seasonal_link)-1]


    def find_element_by_text(self, text, type_='*'):
        return WebDriverWait(self.driver, 10).until(
            expected_conditions.presence_of_element_located((By.XPATH,
                                                             f"//{type_}[text()='{text}']")))

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.driver.quit()


def main():
    with SolarEdgeConnection() as session:
        power = session.get_current_generation_power()
        logger.info(f'Current power measured as {power} kW')

    # assert "Python" in driver.title
    # elem = driver.find_element_by_name("q")
    # elem.clear()
    # elem.send_keys("pycon")
    # elem.send_keys(Keys.RETURN)
    # assert "No results found." not in driver.page_source


if __name__ == '__main__':
    main()
