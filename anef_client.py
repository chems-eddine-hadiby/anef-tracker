import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

ANEF_URL = "https://administration-etrangers-en-france.interieur.gouv.fr/particuliers/"
API_URL = "https://administration-etrangers-en-france.interieur.gouv.fr/api/anf/dossier-stepper"


def _build_driver():
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--remote-debugging-port=9222")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def fetch_date_statut(username, password, timeout=20):
    driver = _build_driver()
    wait = WebDriverWait(driver, timeout)

    try:
        driver.get(ANEF_URL)
        time.sleep(3)

        wait.until(EC.element_to_be_clickable((By.XPATH,
            "//*[contains(text(),'SE CONNECTER') or contains(text(),'Se connecter')]"
        ))).click()

        def fill(selector, value):
            el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            driver.execute_script("""
                arguments[0].focus();
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('input',  {bubbles:true}));
                arguments[0].dispatchEvent(new Event('change', {bubbles:true}));
            """, el, value)

        fill("input[name='username'], input[type='email']", username)
        fill("input[name='password'], input[type='password']", password)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']").click()

        wait.until(EC.url_contains("administration-etrangers-en-france.interieur.gouv.fr"))
        time.sleep(4)

        result = driver.execute_async_script("""
            const done = arguments[arguments.length - 1];
            fetch(arguments[0], { credentials: 'include', headers: { Accept: 'application/json' } })
            .then(r => r.json().then(data => done(data)))
            .catch(e => done({ error: e.toString() }));
        """, API_URL)

        if not isinstance(result, dict):
            raise RuntimeError("Unexpected API response")
        if "error" in result:
            raise RuntimeError(f"API call failed: {result['error']}")

        dossier = result.get("dossier") or {}
        date_statut = dossier.get("date_statut")
        if not date_statut:
            raise RuntimeError("date_statut missing from API response")

        return date_statut

    except Exception as exc:
        raise RuntimeError(f"ANEF login/check failed: {exc}") from exc
    finally:
        driver.quit()
