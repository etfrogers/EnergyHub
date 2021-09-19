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

from solaredgeoptimiser.config import config

MONITORING_URL = 'https://monitoring.solaredge.com'

DASHBOARD_URL = f"{MONITORING_URL}/solaredge-web/p/site/{config['solar-edge-site-id']}/#/dashboard"

CHROMEDRIVER_PATH = "/Users/user/bin/chromedriver"
logger = logging.getLogger(__name__)


class SolarEdgeAuthenticationError(Exception):
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
        self.check_login()

    def check_login(self):
        self.go_to_dashboard()
        try:
            site_name = WebDriverWait(self.driver, 10).until(
                expected_conditions.presence_of_element_located((By.ID, "se-siteDetailsPanel-name")))
            if not ('Dashboard' in self.driver.title and '4 Dene Road' in site_name.text):
                raise SolarEdgeAuthenticationError()
        except TimeoutException:
            raise SolarEdgeAuthenticationError()

    def go_to_dashboard(self):
        self.driver.get(DASHBOARD_URL)

    def login_using_cached_cookies(self):
        logger.debug('Reloading cached cookies')
        # visit root site to allow cookie setting (can only be set for current domain)
        self.driver.get(MONITORING_URL)
        with open(files('solaredgeoptimiser').joinpath('cookies.json'), 'r') as file:
            cookies = json.load(file)
        for cookie in cookies:
            self.driver.add_cookie(cookie)

    def start_chrome(self):
        options = Options()
        options.add_argument("--window-size=1920x1080")
        options.add_argument("--verbose")
        self.driver = webdriver.Chrome(options=options, executable_path=CHROMEDRIVER_PATH)

    def get_current_generation_power(self) -> float:
        raise NotImplementedError('Fails as component ID is not consistent. Can be retrieved from API')
        elem = WebDriverWait(self.driver, 10).until(
            expected_conditions.presence_of_element_located((By.ID, 'component-2085')))
        power, units = elem.text.split(' ')
        assert units == 'kW'
        power = float(power)
        return power

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
